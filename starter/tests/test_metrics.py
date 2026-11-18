"""checks/metrics.py: the numbers the editor and the evaluators trust."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json

import  pytest

from    helpers                         import  ROOT, dev_case
from    plainedit.checks.metrics        import  count_words, detected_issues, find_issues, issue_count
from    plainedit.checks.metrics        import  issue_score, length_ratio, measure, split_sentences
from    plainedit.config                import  EditorConfig


EDITOR = EditorConfig()
SWAPS  = json.loads((ROOT / "data" / "word_swaps.json").read_text(encoding="utf-8"))


#==========================================================================
# Sentences
#==========================================================================
def test_sentences_split_on_dots_and_lines_but_not_on_am_pm() -> None:
    """
    Pin the sentence splitter: a.m./p.m. and Mr. do not end a sentence, line
    breaks do.
    """
    text = "Open at 8 a.m. on Monday. Ask Mr. Lee.\nBring ID!"
    assert split_sentences(text, editor=EDITOR) == ["Open at 8 a.m. on Monday.", "Ask Mr. Lee.", "Bring ID!"]


#==========================================================================
# Count words ignores lone punctuation
#==========================================================================
def test_count_words_ignores_lone_punctuation() -> None:
    """
    Pin the word count: tokens without a letter or digit do not count.
    """
    assert count_words("Pay $5 - now , please") == 4


#==========================================================================
# Each issue type
#==========================================================================
@pytest.mark.parametrize(
    ("text", "issue", "expected"),
    [
        ("Applications shall be submitted by Friday.", "shall", 1),
        ("The form must be signed by the owner.", "passive", 1),
        ("The fee was not paid on time.", "passive", 1),
        ("We will send the form on Friday.", "passive", 0),
        ("We need a decision and the speed is good.", "passive", 0),
        ("The office will make a decision on Monday.", "hidden_verb", 1),
        ("You will not be admitted unless you have a ticket.", "double_negative", 1),
        ("It is not uncommon to wait.", "double_negative", 1),
        ("You may enter if you have a ticket.", "double_negative", 0),
        ("Please utilize the side door prior to noon.", "complex_words", 2),
        ("In the event that it rains, we use the hall.", "complex_words", 1),
    ],
)
def test_each_issue_type_is_found_or_not(text: str, issue: str, expected: int) -> None:
    """
    Pin one detector per row: the number of hits of one issue type in a sentence.

    Input:
        . text          : one sentence
        . issue         : the issue type
        . expected      : how many hits
    """
    assert len(find_issues(text, editor=EDITOR, swaps=SWAPS)[issue]) == expected


#==========================================================================
# Long sentence uses the configured limit
#==========================================================================
def test_long_sentence_uses_the_configured_limit() -> None:
    """
    Pin that a sentence over sentence_limit words is a long sentence.
    """
    text = " ".join(["word"] * 26) + ". Short one."
    found = find_issues(text, editor=EDITOR, swaps=SWAPS)
    assert len(found["long_sentence"]) == 1
    assert measure(text, editor=EDITOR, swaps=SWAPS)["max_sentence_words"] == 26


#==========================================================================
# measure and the score
#==========================================================================
def test_issue_score_is_the_weighted_sum() -> None:
    """
    Pin issue_score = sum of count * weight from the config.
    """
    counts = {"long_sentences": 1, "passive_hits": 2, "shall_count": 1, "complex_words": 3, "hidden_verbs": 1, "double_negatives": 0}
    assert issue_score(counts, editor=EDITOR) == 2 * 1 + 2 * 2 + 2 * 1 + 1 * 3 + 2 * 1


#==========================================================================
# Measure of the plain case is zero
#==========================================================================
def test_measure_of_the_plain_case_is_zero() -> None:
    """
    Pin that the already-plain notice has issue_score 0 and no detected issue.
    """
    text    = dev_case("D09")["inputs"]["text"]
    metrics = measure(text, editor=EDITOR, swaps=SWAPS)
    assert metrics["issue_score"] == 0
    assert detected_issues(find_issues(text, editor=EDITOR, swaps=SWAPS), editor=EDITOR) == []


#==========================================================================
# Measure keys and issue count agree
#==========================================================================
def test_measure_keys_and_issue_count_agree() -> None:
    """
    Pin the keys of measure() and that issue_count reads the same numbers.
    """
    metrics = measure(dev_case("D08")["inputs"]["text"], editor=EDITOR, swaps=SWAPS)
    assert {"words", "sentences", "max_sentence_words", "avg_sentence_words", "issue_score"} <= set(metrics)
    assert issue_count(metrics, "shall") == metrics["shall_count"] == 1
    assert issue_count(metrics, "long_sentence") == metrics["long_sentences"] >= 1


#==========================================================================
# Length ratio compares word counts
#==========================================================================
def test_length_ratio_compares_word_counts() -> None:
    """
    Pin length_ratio = words(rewrite) / words(original), rounded to 2 digits.
    """
    assert length_ratio("one two three four", "one two") == 0.5
    assert length_ratio("", "one") == 1.0
