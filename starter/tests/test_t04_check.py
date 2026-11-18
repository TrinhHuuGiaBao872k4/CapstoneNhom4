"""T04 (LangGraph): after_check (pass / loop / pick_best) and the feedback list."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
import  operator
from    functools                       import  partial
from    pathlib                         import  Path
from    typing                          import  Annotated, Any, TypedDict

import  pytest
from    langgraph.graph                 import  END, START, StateGraph

from    helpers                          import  ROOT, plain_deps
from    plainedit.checks.metrics         import  find_issues, measure
from    plainedit.config                 import  EditorConfig
from    plainedit.graph.nodes.check      import  build_feedback, check_node, check_passes, obligation_kept
from    plainedit.graph.nodes.pick_best  import  pick_best_node
from    plainedit.graph.routes           import  after_check


EDITOR = EditorConfig()
SWAPS  = json.loads((ROOT / "data" / "word_swaps.json").read_text(encoding="utf-8"))


#==========================================================================
# T04: after_check
#==========================================================================
@pytest.mark.parametrize(
    ("passed", "rounds", "expected"),
    [
        (True, 1, "editor_review"),
        (True, 3, "editor_review"),
        (False, 1, "write"),
        (False, 2, "write"),
        (False, 3, "pick_best"),
    ],
)
def test_t04_after_check_routes_pass_loop_and_limit(passed: bool, rounds: int, expected: str) -> None:
    """
    Pin T04: pass goes to the editor, a fail loops until max_rounds, then pick_best.

    Input:
        . passed        : the check result
        . rounds        : rewrites done
        . expected      : the node name
    """
    assert after_check({"passed": passed, "rounds": rounds}, max_rounds=3) == expected


#==========================================================================
# T04 after check uses the limit it is given
#==========================================================================
def test_t04_after_check_uses_the_limit_it_is_given() -> None:
    """
    Pin T04: max_rounds is a parameter, not a constant.
    """
    assert after_check({"passed": False, "rounds": 1}, max_rounds=1) == "pick_best"
    assert after_check({"passed": False, "rounds": 4}, max_rounds=5) == "write"


#==========================================================================
# T04: the feedback list
#==========================================================================
def test_t04_feedback_lists_missing_facts_first_then_each_issue() -> None:
    """
    Pin T04: FACTS MISSING comes first with the facts; long sentences, complex
    words, passive, shall, hidden verb, negatives and length follow.
    """
    text  = "Applications shall be submitted prior to the date. " + " ".join(["word"] * 30) + "."
    found = find_issues(text, editor=EDITOR, swaps=SWAPS)
    lines = build_feedback(found, missing=["15 March 2027", "$45"], ratio=0.2, editor=EDITOR, swaps=SWAPS)
    assert lines[0] == "FACTS MISSING, copy them exactly: 15 March 2027; $45"
    joined = "\n".join(lines)
    assert "Sentence too long (30 words, limit 25)" in joined
    assert 'Complex word "prior to": write "before"' in joined
    assert 'Passive voice "be submitted"' in joined
    assert '"shall be submitted prior": write "must"' in joined or '"shall be submitted' in joined
    assert "Length is 0.2 of the original" in joined


#==========================================================================
# T04 feedback is empty for a clean rewrite and caps quotes per issue
#==========================================================================
def test_t04_feedback_is_empty_for_a_clean_rewrite_and_caps_quotes_per_issue() -> None:
    """
    Pin T04: nothing wrong gives []; at most three quotes per issue type.
    """
    clean = find_issues("We open at 8 a.m.", editor=EDITOR, swaps=SWAPS)
    assert build_feedback(clean, missing=[], ratio=1.0, editor=EDITOR, swaps=SWAPS) == []
    many  = find_issues("It was done. It was made. It was sent. It was paid. It was held.", editor=EDITOR, swaps=SWAPS)
    lines = build_feedback(many, missing=[], ratio=1.0, editor=EDITOR, swaps=SWAPS)
    assert len([line for line in lines if line.startswith("Passive voice")]) == 3


#==========================================================================
# The pass rule and the check node (given)
#==========================================================================
def test_check_passes_needs_every_condition() -> None:
    """
    Pin the pass rule: facts, obligations, score at the target and not above
    the original's, sentence limit and length ratio.
    """
    good = {"issue_score": 3, "max_sentence_words": 25}
    assert check_passes(good, [], 1.0, editor=EDITOR, before=10)
    assert not check_passes(good, ["$5"], 1.0, editor=EDITOR, before=10)
    assert not check_passes(good, [], 1.0, editor=EDITOR, before=10, obligation=False)
    assert not check_passes({**good, "issue_score": 4}, [], 1.0, editor=EDITOR, before=10)
    assert not check_passes({**good, "max_sentence_words": 26}, [], 1.0, editor=EDITOR, before=10)
    assert not check_passes(good, [], 0.2, editor=EDITOR, before=10)
    assert not check_passes(good, [], 1.5, editor=EDITOR, before=10)


#==========================================================================
# A rewrite may not be worse than the original
#==========================================================================
def test_a_rewrite_may_not_be_worse_than_the_original() -> None:
    """
    Pin the "not worse" rule: an already plain notice (score 0) needs a
    rewrite at 0, and a notice at 2 needs 2 or less, even though the target is 3.
    """
    assert check_passes({"issue_score": 0, "max_sentence_words": 10}, [], 1.0, editor=EDITOR, before=0)
    assert not check_passes({"issue_score": 2, "max_sentence_words": 10}, [], 1.0, editor=EDITOR, before=0)
    assert not check_passes({"issue_score": 3, "max_sentence_words": 10}, [], 1.0, editor=EDITOR, before=2)


#==========================================================================
# Obligation kept needs a must when the notice says shall
#==========================================================================
def test_obligation_kept_needs_a_must_when_the_notice_says_shall() -> None:
    """
    Pin obligation_kept: no "shall" in the notice means nothing to keep; with
    "shall" the rewrite needs "must" (any case), not an imperative or "may".
    """
    assert obligation_kept("Pay the fee.", "Pay the fee now.")
    assert obligation_kept("The holder shall pay.", "The holder MUST pay.")
    assert not obligation_kept("The holder shall pay.", "Pay the fee.")
    assert not obligation_kept("The holder shall pay.", "The holder may pay.")


#==========================================================================
def test_t04_check_node_records_one_attempt_and_the_feedback(tmp_path: Path) -> None:
    """
    Pin T04 through the check node: a rewrite that lost a fact fails, is
    recorded as an attempt with its metrics, and the feedback names the fact.

    Input:
        . tmp_path      : temporary folder for the deps
    """
    deps  = plain_deps(tmp_path)
    state = {
        "source_text": "Pay $45 by 15 March 2027 at Room 204.",
        "rewrite": "Pay $45 at Room 204.",
        "facts": ["$45", "15 March 2027", "Room 204"],
        "metrics_before": {"issue_score": 10},
        "rounds": 1,
    }
    out = check_node(state, deps=deps)
    attempt = out["attempts"][0]
    assert out["passed"] is False and attempt["round"] == 1 and attempt["facts_missing"] == ["15 March 2027"]
    assert out["feedback"][0] == "FACTS MISSING, copy them exactly: 15 March 2027"
    assert attempt["metrics"] == measure("Pay $45 at Room 204.", editor=deps.config.editor, swaps=deps.swaps)


#==========================================================================
# T04: the loop in a small graph
#==========================================================================
class LoopState(TypedDict, total=False):
    """
    Purpose: a minimal state for the loop test, so T04 does not need T03.
    """

    source_text: str
    facts: list[str]
    metrics_before: dict[str, Any]
    rewrite: str
    feedback: list[str]
    passed: bool
    rounds: int
    status: str
    reason: str
    attempts: Annotated[list[dict[str, Any]], operator.add]
    log: Annotated[list[str], operator.add]


#==========================================================================
# Scripted write
#==========================================================================
def scripted_write(state: LoopState, *, texts: list[str], seen: list[list[str]]) -> dict[str, Any]:
    """
    Play the model: return the next prepared rewrite and remember the feedback it received.

    Input:
        . state         : rounds and feedback
        . texts         : one rewrite per round
        . seen          : appended with the feedback of each call
    Output:
        . update        : rewrite, rounds + 1
    """
    seen.append(list(state.get("feedback", [])))
    return {"rewrite": texts[state["rounds"]], "rounds": state["rounds"] + 1}


#==========================================================================
# T04 the loop feeds the failure back and stops at the limit
#==========================================================================
def test_t04_the_loop_feeds_the_failure_back_and_stops_at_the_limit(tmp_path: Path) -> None:
    """
    Pin T04 in a graph write -> check -> (write | pick_best): round 1 loses
    facts, round 2 receives FACTS MISSING and restores them but stays too
    complex, round 3 loses a fact again and is the last: pick_best keeps
    round 2, the only attempt with every fact.

    Input:
        . tmp_path      : temporary folder for the deps
    """
    deps  = plain_deps(tmp_path)
    seen: list[list[str]] = []
    texts = [
        "Please utilize the form.",
        "Please utilize the form and commence payment of $45 prior to 15 March 2027 in the amount of $45 subsequent to the event.",
        "Please utilize and terminate the form and pay $45 prior to the event.",
    ]

    #----------------------------------------------------------------------
    # Wire write -> check -> loop
    #----------------------------------------------------------------------
    graph = StateGraph(LoopState)
    graph.add_node("write", partial(scripted_write, texts=texts, seen=seen))
    graph.add_node("check", partial(check_node, deps=deps), input_schema=LoopState)
    graph.add_node("pick_best", pick_best_node, input_schema=LoopState)
    graph.add_edge(START, "write")
    graph.add_edge("write", "check")
    graph.add_conditional_edges("check", partial(after_check, max_rounds=3), {"editor_review": END, "write": "write", "pick_best": "pick_best"})
    graph.add_edge("pick_best", END)

    #----------------------------------------------------------------------
    # Run and check
    #----------------------------------------------------------------------
    out = graph.compile().invoke({
        "source_text": "Pay $45 by 15 March 2027 with the form, which you must utilize prior to the date and so on.",
        "facts": ["$45", "15 March 2027"],
        "metrics_before": {"issue_score": 20},
        "rounds": 0,
    })
    assert out["rounds"] == 3 and len(out["attempts"]) == 3
    assert seen[0] == [] and seen[1][0].startswith("FACTS MISSING") and "$45" in seen[1][0]
    assert out["rewrite"] == texts[1] and out["status"] == "needs_editor"


#==========================================================================
# pick_best (given)
#==========================================================================
def attempt(round_number: int, score: int, missing: list[str]) -> dict[str, Any]:
    """
    Build one attempt record for the pick_best tests.

    Input:
        . round_number  : the round
        . score         : its issue_score
        . missing       : its missing facts
    Output:
        . attempt       : the dict check_node would record
    """
    return {"round": round_number, "text": f"text {round_number}", "metrics": {"issue_score": score}, "facts_missing": missing}


#==========================================================================
# Pick best prefers complete facts then the lowest score then the ...
#==========================================================================
def test_pick_best_prefers_complete_facts_then_the_lowest_score_then_the_earlier_round() -> None:
    """
    Pin pick_best: a fact-safe attempt beats a better score that lost a fact;
    ties go to the earlier round.
    """
    out = pick_best_node({"attempts": [attempt(1, 1, ["$5"]), attempt(2, 6, []), attempt(3, 4, []), attempt(4, 4, [])]})
    assert out["rewrite"] == "text 3" and out["status"] == "needs_editor"
    assert "round 3 kept every fact" in out["reason"]


#==========================================================================
# Pick best says so when every attempt lost a fact
#==========================================================================
def test_pick_best_says_so_when_every_attempt_lost_a_fact() -> None:
    """
    Pin pick_best: with no fact-safe attempt, keep the one that lost the
    fewest facts and say an editor must restore it.
    """
    out = pick_best_node({"attempts": [attempt(1, 1, ["$5", "Room 1"]), attempt(2, 9, ["$5"])]})
    assert out["rewrite"] == "text 2"
    assert "every attempt lost a fact" in out["reason"] and "$5" in out["reason"]
