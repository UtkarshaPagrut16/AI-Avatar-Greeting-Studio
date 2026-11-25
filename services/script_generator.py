"""
script_generator.py - Creates the greeting script.

Flow:
    1. build_prompts()      -> turn the form details into instructions for the LLM
    2. OllamaClient.chat()  -> the local LLM writes the greeting   (AI step)
    3. clean_llm_output()   -> remove extras such as "Here is your greeting:"
    4. enforce_length()     -> cut overly long answers at a sentence boundary
    5. If the LLM fails and fallback is allowed -> template_generator (NOT AI)

The returned dictionary always says which generator was used:
    source = "llm"       -> written by the local language model
    source = "template"  -> written from fixed templates (no AI)
"""
import re

import config
from services.llm_service import LLMError, OllamaClient
from services.template_generator import default_event_name, generate_template_greeting

TONE_GUIDE = {
    "Friendly": "warm, casual and cheerful, like talking to a good friend",
    "Formal": "polite, respectful and professional; no slang and no jokes",
    "Funny": "light-hearted with one gentle, clean joke; never insulting or sarcastic",
    "Heartfelt": "sincere, emotional and caring, from the heart",
}

OCCASION_GUIDE = {
    "Birthday": "wish them a happy birthday and a great year ahead",
    "Anniversary": "wish them a happy anniversary and celebrate their relationship or milestone",
    "Congratulations": "congratulate them on their achievement",
    "Thank You": "thank them warmly for their help or kindness",
    "Welcome": "welcome them warmly (to a new team, home, class or group)",
    "Festival": "wish them a happy festival",
    "Custom": "send good wishes for the occasion described",
}

LANGUAGE_GUIDE = {
    "en": "Write in simple, natural English.",
    "hinglish": ("Write in Hinglish: Hindi words written ONLY in English (Latin) letters, "
                 "for example 'Aapko janamdin ki dher saari shubhkamnayein'. Do not use Devanagari."),
    "hi": "Write entirely in Hindi using Devanagari script. Keep the names exactly as given.",
}

SYSTEM_PROMPT = (
    "You write short spoken greeting scripts for an animated cartoon avatar video. "
    "The avatar speaks on behalf of the sender. "
    "Output ONLY the exact words the avatar will say, as one short paragraph. "
    "Do not add a title, quotation marks, emojis, hashtags, bullet points, "
    "stage directions like (smiles), or any explanation before or after the greeting. "
    "Always keep the greeting kind, respectful and suitable for all ages."
)


def build_prompts(details):
    """Return (system_prompt, user_prompt) built from the validated form details."""
    low, high = config.LENGTHS[details["length"]]
    event = default_event_name(details["occasion"], details.get("occasion_name", ""))
    occasion_text = details["occasion"]
    if details["occasion"] in ("Festival", "Custom"):
        occasion_text = f"{details['occasion']} ({event})"

    lines = [
        f"Recipient name: {details['recipient']}",
        f"Sender name: {details['sender']}",
        f"Occasion: {occasion_text} - {OCCASION_GUIDE[details['occasion']]}.",
        f"Tone: {details['tone']} - {TONE_GUIDE[details['tone']]}.",
        f"Length: between {low} and {high} words.",
        LANGUAGE_GUIDE[details["language"]],
        f"Start by addressing {details['recipient']} by name. "
        f"End with a short sign-off from {details['sender']}.",
    ]
    if details.get("message"):
        lines.append(
            "Include the meaning of this personal message from the sender naturally "
            f"in the greeting: \"{details['message']}\""
        )
    lines.append("Now write the greeting script.")
    return SYSTEM_PROMPT, "\n".join(lines)


# --------------------------------------------------------------------------
# Cleaning the model's answer
# --------------------------------------------------------------------------
_PREFIX_RE = re.compile(
    r"^\s*(sure|certainly|of course|okay|ok|here(?:'s| is)|greeting script|script|greeting)\b[^\n:]*:\s*",
    re.IGNORECASE,
)
_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")
_STAGE_RE = re.compile(r"[\(\[][^\)\]]{0,40}[\)\]]")  # (smiles) or [waves]


def clean_llm_output(text):
    """Remove labels, markdown, emojis, stage directions and wrapping quotes."""
    text = text.replace("\r", "")
    text = _PREFIX_RE.sub("", text, count=1)
    # Drop trailing notes such as "Note: ..." that small models sometimes add.
    text = re.split(r"\n\s*(?:note|explanation|word count)\s*:", text, flags=re.IGNORECASE)[0]
    text = _STAGE_RE.sub("", text)
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"[#_`>~*]", "", text)   # markdown symbols such as **bold**
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("\"'“”‘’ ")
    return text


def word_count(text):
    return len(text.split())


def enforce_length(text, max_words):
    """If the text is far too long, cut it at the last full sentence that fits."""
    limit = int(max_words * 1.3)
    if word_count(text) <= limit:
        return text
    sentences = re.split(r"(?<=[.!?।])\s+", text)
    kept = []
    for sentence in sentences:
        if word_count(" ".join(kept + [sentence])) > limit:
            break
        kept.append(sentence)
    return " ".join(kept) if kept else " ".join(text.split()[:limit])


def ensure_personalised(text, details):
    """Make sure the recipient's name appears (Latin-script languages only)."""
    if details["language"] == "hi":
        return text  # the model may write the name in Devanagari; that is fine
    if details["recipient"].lower() not in text.lower():
        if text[1:2].islower() and not text.startswith("I "):
            text = text[0].lower() + text[1:]
        text = f"Dear {details['recipient']}, {text}"
    return text


# --------------------------------------------------------------------------
# Main entry point used by app.py
# --------------------------------------------------------------------------
def generate_script(details, client=None, allow_fallback=None):
    """Generate a greeting. Returns a dict with script, source, model and notice."""
    client = client or OllamaClient()
    allow_fallback = config.ALLOW_TEMPLATE_FALLBACK if allow_fallback is None else allow_fallback
    system_prompt, user_prompt = build_prompts(details)
    _, high = config.LENGTHS[details["length"]]

    try:
        raw = client.chat(system_prompt, user_prompt)
        script = clean_llm_output(raw)
        if word_count(script) < 5:
            raise LLMError("The model's answer was too short to use.")
        script = enforce_length(ensure_personalised(script, details), high)
        return {
            "script": script,
            "source": "llm",
            "model": client.model,
            "notice": f"Written by the local AI model {client.model} running in Ollama on this computer.",
            "word_count": word_count(script),
        }
    except LLMError as exc:
        reason = getattr(exc, "reason", LLMError.reason)
        if str(exc) and type(exc) is LLMError:
            reason = str(exc)
        if not allow_fallback:
            raise
        script = generate_template_greeting(details)
        return {
            "script": script,
            "source": "template",
            "model": None,
            "notice": (f"Template fallback used because: {reason} "
                       "This text was produced from fixed templates and was NOT written by an AI model."),
            "fallback_reason": reason,
            "word_count": word_count(script),
        }
