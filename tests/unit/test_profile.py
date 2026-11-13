import pytest

from lets import profile
from lets.core import LetsError


def test_defaults_are_written_and_read_back():
    profile.write({})
    assert profile.answer("build") == "pair"
    assert profile.answer("length") == "medium"
    assert profile.answer("questions") == "one"
    assert profile.answer("updates") == "on"


def test_message_length_splits_never_squeezes():
    text = profile.choice_text("length", "short")
    assert "about 250 words" in text and "Split, don't squeeze" in text


def test_a_custom_length_is_recognised():
    profile.write({"length": profile.choice_text("length", "custom", 400)})
    assert profile.answer("length") == "custom"
    assert profile.summary_line("length") == "about 400 words"


def test_changing_one_answer_keeps_the_others():
    profile.write({"build": profile.choice_text("build", "agent")})
    have = profile.current()
    have.pop(profile.choice("length").heading)
    profile.write({"length": profile.choice_text("length", "natural")}, have)
    assert profile.answer("build") == "agent" and profile.answer("length") == "natural"


def test_text_sections_default_to_letss_text():
    profile.write({})
    assert profile.summary_line("teaching") == "LETS's default"


@pytest.mark.parametrize(
    "word, key", [("len", "length"), ("build", "build"), ("q", "questions"), ("code", "code-style")]
)
def test_short_forms(word, key):
    assert profile.resolve(word) == key


def test_ambiguous_short_form_is_refused():
    with pytest.raises(LetsError):
        profile.resolve("zz")
