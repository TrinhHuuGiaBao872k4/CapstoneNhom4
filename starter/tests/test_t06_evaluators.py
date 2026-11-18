"""T06 (LangSmith): facts_kept and issue_score_improved, and the experiment on the fake backend."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  pytest

from    plainedit.evaluation.evaluators  import  default_evaluators, findings_grounded, planted_recall
from    plainedit.evaluation.evaluators  import  facts_kept, issue_score_improved, sentence_limit_ok, traps_ok


#==========================================================================
# T06: facts_kept
#==========================================================================
def test_t06_facts_kept_is_all_or_nothing() -> None:
    """
    Pin T06: 1.0 only when every reference fact is in the rewrite; a lost
    fact gives 0.0 and the comment names it.
    """
    reference = {"facts": ["$45", "15 March 2027"]}
    ok  = facts_kept({}, {"rewrite": "Pay 45 dollars by March 15, 2027."}, reference)
    bad = facts_kept({}, {"rewrite": "Pay $45 soon."}, reference)
    assert ok["score"] == 1.0
    assert bad["score"] == 0.0 and "15 March 2027" in bad["comment"] and "$45" not in bad["comment"]


#==========================================================================
# T06: issue_score_improved
#==========================================================================
@pytest.mark.parametrize(
    ("before", "after", "score"),
    [(10, 2, 0.8), (10, 10, 0.0), (10, 12, 0.0), (4, 0, 1.0), (0, 0, 1.0), (0, 3, 0.0)],
)
def test_t06_issue_score_improved_cases(before: int, after: int, score: float) -> None:
    """
    Pin T06: the share of the score removed, never below 0; a notice that
    started at 0 scores 1.0 only if it stays at 0.

    Input:
        . before        : issue_score of the original
        . after         : issue_score of the rewrite
        . score         : the expected evaluator score
    """
    out = issue_score_improved({}, {"metrics_before": {"issue_score": before}, "metrics_after": {"issue_score": after}}, {})
    assert out["score"] == score and out["comment"] == f"{before} -> {after}"


#==========================================================================
# The other evaluators (given)
#==========================================================================
def test_the_given_evaluators_score_what_they_say() -> None:
    """
    Pin sentence_limit_ok, findings_grounded, planted_recall and traps_ok on hand-made outputs.
    """
    outputs = {
        "original": "Applications shall be submitted by Friday.",
        "rewrite": "You must submit your application by Friday.",
        "findings": [{"issue": "shall", "quote": "Applications shall be submitted", "rule_id": "x"}],
        "metrics_after": {"max_sentence_words": 8, "long_sentences": 0, "passive_hits": 0, "shall_count": 0,
                          "complex_words": 0, "hidden_verbs": 0, "double_negatives": 0},
    }

    #----------------------------------------------------------------------
    # Check each evaluator
    #----------------------------------------------------------------------
    reference = {"sentence_limit": 25, "planted": ["shall", "passive"], "required_terms": ["must"], "forbidden_terms": ["waived"]}
    assert sentence_limit_ok({}, outputs, reference) is True
    assert findings_grounded({}, outputs, reference) is True
    assert findings_grounded({}, {**outputs, "findings": [{"issue": "x", "quote": "not there", "rule_id": "x"}]}, reference) is False
    assert planted_recall({}, outputs, reference) == 1.0
    assert planted_recall({}, {**outputs, "findings": [], "metrics_after": {**outputs["metrics_after"], "passive_hits": 2}}, reference) == 0.5
    assert planted_recall({}, outputs, {**reference, "planted": []}) == 1.0
    assert traps_ok({}, outputs, reference) is True
    assert traps_ok({}, {**outputs, "rewrite": "The fee is waived."}, reference) is False
    assert traps_ok({}, {**outputs, "rewrite": "You shall submit."}, reference) is False


#==========================================================================
# Every evaluator takes only the names langsmith and the local ...
#==========================================================================
def test_every_evaluator_takes_only_the_names_langsmith_and_the_local_runner_know() -> None:
    """
    Pin the evaluator signatures: parameters are inputs, outputs, reference_outputs only.
    """
    import  inspect

    for evaluator in default_evaluators():
        assert list(inspect.signature(evaluator).parameters) == ["inputs", "outputs", "reference_outputs"], evaluator.__name__
