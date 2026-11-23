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
    #----------------------------------------------------------------------
    # Format missing facts and per-issue feedback lines
    #----------------------------------------------------------------------
    lines: list[str] = []
    if missing:
        lines.append(f"FACTS MISSING, copy them exactly: {'; '.join(missing)}")
    swap_map: dict[str, str] = {}
    for row in swaps:
        vals = list(row.values())
        if len(vals) >= 2:
            complex_w = row.get("complex") or row.get("avoid") or row.get("from") or vals[0]
            simple_w  = row.get("simple") or row.get("use") or row.get("to") or vals[1]
            swap_map[complex_w.lower()] = simple_w

    for q in found.get("long_sentence", [])[:3]:
        lines.append(f"Sentence too long ({len(q.split())} words, limit {editor.sentence_limit}): {q}")

    for q in found.get("complex_words", [])[:3]:
        simple = swap_map.get(q.lower(), "")
        if simple:
            lines.append(f'Complex word "{q}": write "{simple}"')
        else:
            lines.append(f'Complex word "{q}": use a simpler word')

    for q in found.get("passive", [])[:3]:
        lines.append(f'Passive voice "{q}": rewrite in active voice')

    for q in found.get("shall", [])[:3]:
        lines.append(f'Avoid shall in "{q}": write "must"')

    for q in found.get("hidden_verb", [])[:3]:
        lines.append(f'Hidden verb "{q}": use the direct verb')

    for q in found.get("negatives", [])[:3]:
        lines.append(f'Negative phrasing "{q}": state it positively')

    if ratio < editor.min_length_ratio or ratio > editor.max_length_ratio:
        lines.append(
            f"Length is {ratio:.1f} of the original "
            f"(keep between {editor.min_length_ratio} and {editor.max_length_ratio})"
        )

    return lines


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
