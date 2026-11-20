"""Evaluators: plain code rules, the same functions locally and on LangSmith.

Each takes only (inputs, outputs, reference_outputs) and returns a bool, a
number or {"score", "comment"}; the metric name is the function name.
outputs is the contract of one edit; reference_outputs holds what a correct
edit must keep (facts, planted issue types, sentence limit, trap terms).
"""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    collections.abc                 import  Callable
from    typing                          import  Any

from    plainedit.checks.facts          import  missing_facts  # noqa: F401 (your stop uses it)
from    plainedit.checks.metrics        import  issue_count, normalize_words


#==========================================================================
# facts_kept: the hard one
#==========================================================================
def facts_kept(inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    """
    Score 1.0 when the rewrite still has EVERY reference fact, else 0.0.
    One lost date or amount is a failed edit: no partial credit.

    Input:
        . inputs        : the case inputs (unused)
        . outputs       : the contract; outputs["rewrite"] is read
        . reference_outputs : reference_outputs["facts"], the facts of the notice
    Output:
        . result        : {"score": 1.0 or 0.0, "comment": the missing facts}
    """
    # TODO T06 -- score 1.0 only when missing_facts(reference_outputs["facts"], outputs["rewrite"]) is empty, else 0.0;
    #     put the missing facts in "comment".
    # CHECK: pytest -k t06 -- test_t06_facts_kept_is_all_or_nothing.
    # raise NotImplementedError("T06: facts_kept")
    missing = missing_facts(reference_outputs["facts"], outputs["rewrite"])
    return {
        "score": 0.0 if missing else 1.0,
        "comment": ", ".join(missing) if missing else "all facts kept",
    }


#==========================================================================
# issue_score_improved
#==========================================================================
def issue_score_improved(inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    """
    Score how much the issue_score fell: (before - after) / before, 0.0 when
    it did not fall. A notice that was already plain (before = 0) scores 1.0
    when it stays at 0, else 0.0.

    Input:
        . inputs        : the case inputs (unused)
        . outputs       : the contract; metrics_before and metrics_after issue_score
        . reference_outputs : unused
    Output:
        . result        : {"score": 0.0 .. 1.0, "comment": "before -> after"}
    """
    # TODO T06 -- score = (before - after) / before from metrics_before / metrics_after issue_score, never below 0.0;
    #     if before is 0: 1.0 when after is 0, else 0.0. comment = "before -> after".
    # CHECK: pytest -k t06 -- test_t06_issue_score_improved_cases.
    # raise NotImplementedError("T06: issue_score_improved")
    before = outputs["metrics_before"]["issue_score"]
    after = outputs["metrics_after"]["issue_score"]

    if before == 0:
        score = 1.0 if after == 0 else 0.0
    else:
        score = max(0.0, min(1.0, (before - after) / before))

    return {"score": score, "comment": f"{before} -> {after}"}


#==========================================================================
# sentence_limit_ok
#==========================================================================
def sentence_limit_ok(inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> bool:
    """
    True when the longest sentence of the rewrite is within the limit.

    Input:
        . inputs        : unused
        . outputs       : metrics_after.max_sentence_words
        . reference_outputs : sentence_limit
    Output:
        . ok            : True when max_sentence_words <= sentence_limit
    """
    return outputs["metrics_after"]["max_sentence_words"] <= reference_outputs["sentence_limit"]


#==========================================================================
# findings_grounded
#==========================================================================
def findings_grounded(inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> bool:
    """
    True when every finding quotes words that are in the original. No
    findings (v1 makes none) is vacuously True: read it with planted_recall.

    Input:
        . inputs        : unused
        . outputs       : findings and original
        . reference_outputs : unused
    Output:
        . ok            : True when all quotes are in the original
    """
    haystack = f" {normalize_words(outputs['original'])} "
    return all(f" {normalize_words(item['quote'])} " in haystack for item in outputs["findings"])


#==========================================================================
# planted_recall
#==========================================================================
def planted_recall(inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> float:
    """
    Share of the planted issue types that are dealt with: named in a finding,
    or gone from the rewrite (the metric count fell to 0). A notice with no
    planted issue scores 1.0.

    Input:
        . inputs        : unused
        . outputs       : findings, metrics_before, metrics_after
        . reference_outputs : planted (issue types)
    Output:
        . recall        : 0.0 .. 1.0
    """
    planted = reference_outputs["planted"]
    if not planted:
        return 1.0
    named = {item["issue"] for item in outputs["findings"]}
    dealt = [
        issue for issue in planted
        if issue in named or issue_count(outputs["metrics_after"], issue) == 0
    ]
    return round(len(dealt) / len(planted), 3)


#==========================================================================
# traps_ok
#==========================================================================
def traps_ok(inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> bool:
    """
    True when every required term is in the rewrite (e.g. "must" for a legal
    shall) and no forbidden term is (e.g. "waived" after an injected order).

    Input:
        . inputs        : unused
        . outputs       : rewrite
        . reference_outputs : required_terms, forbidden_terms (lists, may be empty)
    Output:
        . ok            : True when nothing trapped the edit
    """
    text = outputs["rewrite"].lower()
    return (
        all(term.lower() in text for term in reference_outputs["required_terms"])
        and not any(term.lower() in text for term in reference_outputs["forbidden_terms"])
    )


#==========================================================================
# The evaluator set
#==========================================================================
def default_evaluators() -> list[Callable[..., Any]]:
    """
    The evaluators every experiment runs, in report order.

    Output:
        . evaluators    : facts_kept, issue_score_improved, sentence_limit_ok,
                          findings_grounded, planted_recall, traps_ok
    """
    return [facts_kept, issue_score_improved, sentence_limit_ok, findings_grounded, planted_recall, traps_ok]
