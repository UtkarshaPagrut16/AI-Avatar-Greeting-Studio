"""
validators.py - Checks and cleans everything the user types into the form.

Why this exists: the browser form already has basic checks, but anyone can
send a request directly to the server, so the server must validate again.
"""
import re
import unicodedata

import config

NAME_MAX = 40
MESSAGE_MAX = 300
OCCASION_NAME_MAX = 40
SCRIPT_MAX_CHARS = 1200

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# A tiny word list so obviously abusive text is rejected before it reaches
# the LLM. It is intentionally short; the prompt also asks for polite output.
_BLOCKED_WORDS = {"fuck", "shit", "bitch", "bastard", "slut", "whore", "nigger",
                  "chutiya", "madarchod", "bhenchod", "randi"}


class ValidationError(ValueError):
    """Raised when the request is invalid. `errors` maps field -> message."""

    def __init__(self, errors):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


def is_valid_name(name):
    """Letters (any script, including Hindi vowel signs), spaces, . ' - only."""
    if not name or not unicodedata.category(name[0]).startswith("L"):
        return False
    return all(unicodedata.category(ch)[0] in ("L", "M") or ch in " .'-" for ch in name)


def _clean_text(value):
    """Turn any value into a trimmed string with control characters removed."""
    if value is None:
        return ""
    text = _CONTROL_RE.sub("", str(value))
    return re.sub(r"[ \t]+", " ", text).strip()


def contains_blocked_words(text):
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return any(w in _BLOCKED_WORDS for w in words)


def validate_greeting_request(data):
    """Validate the greeting form. Returns a clean dict or raises ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError({"form": "Request body must be a JSON object."})

    errors = {}
    clean = {
        "recipient": _clean_text(data.get("recipient")),
        "sender": _clean_text(data.get("sender")),
        "occasion": _clean_text(data.get("occasion")),
        "occasion_name": _clean_text(data.get("occasion_name")),
        "tone": _clean_text(data.get("tone")),
        "language": _clean_text(data.get("language")) or "en",
        "length": _clean_text(data.get("length")) or "Short",
        "message": _clean_text(data.get("message")),
    }

    for field, label in (("recipient", "Recipient name"), ("sender", "Sender name")):
        value = clean[field]
        if not value:
            errors[field] = f"{label} is required."
        elif len(value) > NAME_MAX:
            errors[field] = f"{label} must be at most {NAME_MAX} characters."
        elif not is_valid_name(value):
            errors[field] = f"{label} may contain only letters, spaces, dots, apostrophes and hyphens."

    if clean["occasion"] not in config.OCCASIONS:
        errors["occasion"] = "Please choose a valid occasion."
    if clean["tone"] not in config.TONES:
        errors["tone"] = "Please choose a valid tone."
    if clean["language"] not in config.LANGUAGES:
        errors["language"] = "Please choose a supported language."
    if clean["length"] not in config.LENGTHS:
        errors["length"] = "Please choose Short or Medium."

    if clean["occasion"] == "Custom" and not clean["occasion_name"]:
        errors["occasion_name"] = "Please describe the custom occasion (e.g. Farewell)."
    if len(clean["occasion_name"]) > OCCASION_NAME_MAX:
        errors["occasion_name"] = f"Occasion name must be at most {OCCASION_NAME_MAX} characters."

    if len(clean["message"]) > MESSAGE_MAX:
        errors["message"] = f"Personal message must be at most {MESSAGE_MAX} characters."

    combined = " ".join([clean["recipient"], clean["sender"], clean["occasion_name"], clean["message"]])
    if "message" not in errors and contains_blocked_words(combined):
        errors["message"] = "Please remove offensive words; greetings must stay respectful."

    if errors:
        raise ValidationError(errors)
    return clean


def validate_script_text(text):
    """Validate the (possibly user-edited) script before speech is generated."""
    script = _clean_text(text).replace("\r", "")
    if not script:
        raise ValidationError({"script": "The script is empty. Generate or type a greeting first."})
    if len(script) > SCRIPT_MAX_CHARS:
        raise ValidationError({"script": f"The script is too long (max {SCRIPT_MAX_CHARS} characters)."})
    if contains_blocked_words(script):
        raise ValidationError({"script": "Please remove offensive words from the script."})
    return script
