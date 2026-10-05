"""CORE-3 normalisation wrapper (benign inputs only)."""

from asg_core.normalise import normalise


def test_plain_text_unchanged():
    n = normalise("Quarterly revenue was 4.2 million.")
    assert n.text == n.original and not n.flags and not n.changes


def test_format_characters_removed_and_flagged():
    n = normalise("re​port ready")
    assert n.text == "report ready" and "format_characters" in n.flags
    assert n.changes["format_chars_removed"] == 1


def test_fullwidth_folds_via_nfkc():
    n = normalise("Ｒｅｐｏｒｔ")   # fullwidth letters
    assert n.text == "Report"


def test_mixed_script_word_flagged_and_ascii_view():
    n = normalise("monthly rеport")   # Cyrillic small ie inside a Latin word
    assert "mixed_script" in n.flags
    assert "report" in n.ascii_view


def test_views_include_ascii_only_when_different():
    assert [k for k, _ in normalise("hello").views()] == ["normalised"]
    assert [k for k, _ in normalise("café").views()] == ["normalised", "ascii"]
