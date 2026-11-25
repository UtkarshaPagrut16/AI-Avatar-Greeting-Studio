"""Tests for prompt building, output cleaning, the template fallback and validation."""
import random

import pytest

import config
from services.llm_service import LLMEmptyResponseError, LLMModelMissingError, LLMTimeoutError, LLMUnavailableError
from services.script_generator import (build_prompts, clean_llm_output, enforce_length, ensure_personalised,
                                       generate_script, word_count)
from services.template_generator import generate_template_greeting
from services.validators import ValidationError, validate_greeting_request, validate_script_text

GOOD_REPLY = ("Happy birthday, Priya! I hope your day is full of laughter and cake. "
              "You make every day brighter. Have a wonderful year ahead. With love, Rahul.")


# ------------------------------------------------------------------ prompts
def test_prompt_contains_every_form_detail(details):
    details.update(message="Can't wait for Goa!", tone="Heartfelt")
    system, user = build_prompts(details)
    for text in ("Priya", "Rahul", "Birthday", "Heartfelt", "Can't wait for Goa!"):
        assert text in user
    assert "ONLY the exact words" in system


def test_prompt_changes_with_tone_language_and_occasion(details):
    base = build_prompts(details)[1]
    for change in ({"tone": "Formal"}, {"language": "hinglish"}, {"language": "hi"},
                   {"occasion": "Festival", "occasion_name": "Diwali"}, {"length": "Medium"}):
        changed = build_prompts({**details, **change})[1]
        assert changed != base, change
    assert "Diwali" in build_prompts({**details, "occasion": "Festival", "occasion_name": "Diwali"})[1]
    assert "Devanagari" in build_prompts({**details, "language": "hi"})[1]


# ------------------------------------------------------------- generation
def test_llm_success_is_labelled_llm(details, fake_llm):
    llm = fake_llm(reply=GOOD_REPLY)
    result = generate_script(details, client=llm)
    assert result["source"] == "llm"
    assert result["model"] == "qwen2.5:1.5b"
    assert "Priya" in result["script"]
    assert len(llm.calls) == 1


def test_llm_output_is_cleaned(details, fake_llm):
    messy = 'Sure! Here is your greeting:\n"**Happy birthday, Priya!** 🎉 (smiles) Have a great day, from Rahul."'
    result = generate_script(details, client=fake_llm(reply=messy))
    assert result["script"] == "Happy birthday, Priya! Have a great day, from Rahul."


@pytest.mark.parametrize("error", [LLMUnavailableError("off"), LLMTimeoutError("slow"),
                                   LLMEmptyResponseError("empty"), LLMModelMissingError("missing")])
def test_failures_use_disclosed_template_fallback(details, fake_llm, error):
    result = generate_script(details, client=fake_llm(error=error))
    assert result["source"] == "template"
    assert result["model"] is None
    assert "NOT written by an AI model" in result["notice"]
    assert "Priya" in result["script"] and "Rahul" in result["script"]


def test_too_short_llm_answer_falls_back(details, fake_llm):
    result = generate_script(details, client=fake_llm(reply="Hi."))
    assert result["source"] == "template"


def test_fallback_can_be_disabled(details, fake_llm):
    with pytest.raises(LLMUnavailableError):
        generate_script(details, client=fake_llm(error=LLMUnavailableError("off")), allow_fallback=False)


# ----------------------------------------------------------- cleaning helpers
def test_enforce_length_cuts_at_sentence_boundary():
    long_text = " ".join(["This is a sentence with seven words."] * 30)
    cut = enforce_length(long_text, 65)
    assert word_count(cut) <= int(65 * 1.3)
    assert cut.endswith(".")


def test_ensure_personalised_adds_missing_name(details):
    assert ensure_personalised("happy birthday to you!", details).startswith("Dear Priya,")
    assert ensure_personalised("Happy birthday Priya!", details) == "Happy birthday Priya!"


def test_clean_removes_trailing_notes():
    assert clean_llm_output("Hello Priya, well done!\nNote: this is 5 words.") == "Hello Priya, well done!"


# ------------------------------------------------------------- templates
@pytest.mark.parametrize("occasion", config.OCCASIONS)
@pytest.mark.parametrize("tone", config.TONES)
@pytest.mark.parametrize("language", list(config.LANGUAGES))
def test_template_exists_for_every_combination(details, occasion, tone, language):
    details.update(occasion=occasion, tone=tone, language=language, occasion_name="Farewell")
    text = generate_template_greeting(details, rng=random.Random(1))
    assert "Priya" in text and "Rahul" in text
    assert "{" not in text


def test_template_includes_personal_message(details):
    details["message"] = "See you in Goa"
    assert "See you in Goa." in generate_template_greeting(details)


# ------------------------------------------------------------- validation
def test_valid_request_is_cleaned(details):
    details["recipient"] = "  Priya  "
    assert validate_greeting_request(details)["recipient"] == "Priya"


def test_hindi_names_are_allowed(details):
    details["recipient"] = "प्रिया"
    assert validate_greeting_request(details)["recipient"] == "प्रिया"


@pytest.mark.parametrize("change, field", [
    ({"recipient": ""}, "recipient"),
    ({"sender": "R2-D2"}, "sender"),
    ({"recipient": "<script>"}, "recipient"),
    ({"recipient": "A" * 41}, "recipient"),
    ({"occasion": "Halloween"}, "occasion"),
    ({"tone": "Angry"}, "tone"),
    ({"language": "fr"}, "language"),
    ({"length": "Huge"}, "length"),
    ({"occasion": "Custom", "occasion_name": ""}, "occasion_name"),
    ({"message": "x" * 301}, "message"),
    ({"message": "you are a bastard"}, "message"),
])
def test_invalid_inputs_are_rejected(details, change, field):
    details.update(change)
    with pytest.raises(ValidationError) as info:
        validate_greeting_request(details)
    assert field in info.value.errors


def test_non_dict_request_is_rejected():
    with pytest.raises(ValidationError):
        validate_greeting_request(["not", "a", "dict"])


def test_script_validation():
    assert validate_script_text("  Hello Priya  ") == "Hello Priya"
    with pytest.raises(ValidationError):
        validate_script_text("   ")
    with pytest.raises(ValidationError):
        validate_script_text("x" * 1201)
