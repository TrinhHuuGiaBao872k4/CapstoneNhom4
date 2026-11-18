"""Node check (code): measure the rewrite, decide pass or fail, write the feedback."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  re
from    typing                          import  Any

from    plainedit.checks.facts          import  missing_facts
from    plainedit.checks.metrics        import  find_issues, length_ratio, measure
from    plainedit.config                import  EditorConfig
from    plainedit.graph.deps            import  Deps
from    plainedit.graph.state           import  EditState


#==========================================================================
# The pass rule
#==========================================================================
def check_passes(
    metrics: dict[str, Any],
    missing: list[str],
    ratio: float,
    *,
    editor: EditorConfig,
    before: int,
    obligation: bool = True,
) -> bool:
    """
    A rewrite passes when no fact is missing, every "shall" of the notice
    survived as "must", its issue_score is at or below the target AND not
    above the original's (a rewrite must not make a plain notice worse), its
    longest sentence is within the limit and its length is between
    min_length_ratio and max_length_ratio of the original.

    Input:
        . metrics       : measure() of the rewrite
        . missing       : facts missing from the rewrite
        . ratio         : length_ratio(original, rewrite)
        . editor        : target_score, sentence_limit, length ratios
        . before        : issue_score of the original
        . obligation    : obligation_kept(original, rewrite)
    Output:
        . passed        : True when the rewrite can go to the editor
    """
    return (
        not missing
        and obligation
        and metrics["issue_score"] <= min(editor.target_score, before)
        and metrics["max_sentence_words"] <= editor.sentence_limit
        and editor.min_length_ratio <= ratio <= editor.max_length_ratio
    )


#==========================================================================
# Obligations
#==========================================================================
def obligation_kept(source: str, rewrite: str) -> bool:
    """
    A notice that says "shall" states an obligation. The guidelines replace
    it by "must": a rewrite of such a notice without any "must" has dropped
    or softened the obligation (an imperative, "may", "should").

    Input:
        . source        : the notice the model read
        . rewrite       : the rewrite
    Output:
        . kept          : True when the notice has no "shall", or the rewrite has "must"
    """
    return re.search(r"\bshall\b", source, re.IGNORECASE) is None or re.search(r"\bmust\b", rewrite, re.IGNORECASE) is not None


#==========================================================================
# The feedback for the next round
#==========================================================================
def build_feedback(
    found: dict[str, list[str]],
    *,
    missing: list[str],
    ratio: float,
    editor: EditorConfig,
    swaps: list[dict[str, str]],
) -> list[str]:
    """
    Turn the failed checks into short, exact lines the model can act on:
    first the missing facts, then each remaining issue with its quote, then a
    length warning. At most three quotes per issue type.

    Input:
        . found         : find_issues() of the rewrite (issue type -> quotes)
        . missing       : facts missing from the rewrite
        . ratio         : length_ratio(original, rewrite)
        . editor        : sentence_limit and the length ratios
        . swaps         : word_swaps rows, to suggest the simple word
    Output:
        . lines         : feedback lines; [] when nothing is wrong
    """
    # TODO T04 -- feedback lines, in this order: FACTS MISSING (the facts joined with '; '), then up to 3 lines per issue type
    #     (long sentence, complex word with its simple word, passive, shall, hidden verb, negatives), then the length warning.
    #     The exact line starts are in the tests.
    # CHECK: pytest -k t04 -- test_t04_feedback_*, test_t04_check_node_*, test_t04_the_loop_*.
    raise NotImplementedError("T04: build_feedback")


#==========================================================================
# check
#==========================================================================
def check_node(state: EditState, *, deps: Deps) -> dict[str, Any]:
    """
    Measure the last rewrite, record it as an attempt, decide pass or fail
    and, on fail, write the feedback for the next round.

    Input:
        . state         : source_text, metrics_before, rewrite, facts, rounds
        . deps          : editor config, word swaps
    Output:
        . update        : attempts (one new), passed, feedback, log
    """

    #----------------------------------------------------------------------
    # Measure the rewrite
    #----------------------------------------------------------------------
    editor  = deps.config.editor
    text    = state["rewrite"]
    metrics = measure(text, editor=editor, swaps=deps.swaps)
    missing = missing_facts(state["facts"], text)
    ratio   = length_ratio(state["source_text"], text)
    kept    = obligation_kept(state["source_text"], text)
    passed  = check_passes(metrics, missing, ratio, editor=editor, before=state["metrics_before"]["issue_score"], obligation=kept)
    found   = find_issues(text, editor=editor, swaps=deps.swaps)
    lines   = [] if passed else build_feedback(found, missing=missing, ratio=ratio, editor=editor, swaps=deps.swaps)
    if not kept:
        lines.append('The notice says "shall" (an obligation): write "must" or "must not" for every obligation')

    #----------------------------------------------------------------------
    # Record the attempt
    #----------------------------------------------------------------------
    attempt = {
        "round": state["rounds"],
        "text": text,
        "metrics": metrics,
        "facts_missing": missing,
        "length_ratio": ratio,
        "obligation_kept": kept,
        "passed": passed,
    }
    return {
        "attempts": [attempt],
        "passed": passed,
        "feedback": lines,
        "log": [
            f"check: round {state['rounds']} issue_score {metrics['issue_score']}, "
            f"max sentence {metrics['max_sentence_words']}, missing facts {missing}, "
            f"{'PASS' if passed else 'FAIL'}"
        ],
    }
