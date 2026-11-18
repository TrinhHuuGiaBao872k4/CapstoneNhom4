"""Node editor_review (human): show the rewrite, wait for approve / edit / reject."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    langgraph.types                 import  interrupt  # noqa: F401 (your stop uses it)

from    plainedit.checks.facts          import  missing_facts
from    plainedit.checks.metrics        import  measure
from    plainedit.graph.deps            import  Deps
from    plainedit.graph.state           import  EditState


#==========================================================================
# What the editor sees
#==========================================================================
def review_payload(state: EditState, *, deps: Deps) -> dict[str, Any]:
    """
    Build the value the graph shows the editor: the notice, the proposed
    rewrite with its metrics and missing facts, the findings, and the
    sentences code removed from the notice.

    Input:
        . state         : original, rewrite, facts, metrics_before, findings, removed
        . deps          : editor config and word swaps for the metrics
    Output:
        . payload       : a JSON-ready dict; "actions" lists approve, edit, reject
    """
    return {
        "draft_id": state["draft_id"],
        "original": state["original"],
        "rewrite": state["rewrite"],
        "metrics_before": state["metrics_before"],
        "metrics_after": measure(state["rewrite"], editor=deps.config.editor, swaps=deps.swaps),
        "facts_missing": missing_facts(state["facts"], state["rewrite"]),
        "findings": state["findings"],
        "removed": state["removed"],
        "note": state.get("reason", ""),
        "actions": ["approve", "edit", "reject"],
    }


#==========================================================================
# editor_review
#==========================================================================
def editor_review(state: EditState, *, deps: Deps) -> dict[str, Any]:
    """
    Pause the graph with interrupt(payload); the editor's decision comes back
    as {"action": "approve" | "edit" | "reject", "text": ..., "note": ...}.
      . approve: status approved, unless a fact is missing: then it stays
        needs_editor (an approval cannot override a lost fact)
      . edit: the editor's text replaces the rewrite; facts are re-checked and
        shown in the reason, not blocking; status approved
      . reject: status rejected, reason = the note

    Input:
        . state         : the state at the interrupt
        . deps          : editor config and word swaps
    Output:
        . update        : decision, rewrite, status, reason, log
    """
    # TODO T05 -- decision = interrupt(review_payload(...)); then apply it: approve (refused with needs_editor when a fact is missing),
    #     edit (the editor's text replaces the rewrite; facts re-checked, shown in the reason), reject (the note is the reason);
    #     any other action raises ValueError. Return decision, rewrite, status, reason, log.
    # CHECK: pytest -k t05 -- the test_t05_* tests (the last ones run the whole graph and need T01-T05).
    raise NotImplementedError("T05: editor_review")
