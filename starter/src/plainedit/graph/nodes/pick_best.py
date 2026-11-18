"""Node pick_best (code): the best attempt when the loop ends without a pass."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    plainedit.graph.state           import  EditState


#==========================================================================
# pick_best
#==========================================================================
def pick_best_node(state: EditState) -> dict[str, Any]:
    """
    Among the attempts, prefer those that kept every fact, then the lowest
    issue_score (the earlier round wins a tie). When every attempt lost a
    fact, keep the one that lost the fewest and say so: the editor must act.

    Input:
        . state         : attempts
    Output:
        . update        : rewrite, status, reason, log
    """

    #----------------------------------------------------------------------
    # Choose among the attempts
    #----------------------------------------------------------------------
    attempts = state["attempts"]
    safe     = [item for item in attempts if not item["facts_missing"]]
    if safe:
        best   = min(safe, key=lambda item: (item["metrics"]["issue_score"], item["round"]))
        status = "needs_editor"
        reason = (
            f"the target was not reached in {len(attempts)} round(s); round {best['round']} kept every fact "
            f"and has the lowest issue_score ({best['metrics']['issue_score']})"
        )
    else:
        best   = min(attempts, key=lambda item: (len(item["facts_missing"]), item["metrics"]["issue_score"], item["round"]))
        status = "needs_editor"
        reason = (
            f"every attempt lost a fact; round {best['round']} lost the fewest: {best['facts_missing']}. "
            "An editor must restore it by hand"
        )

    #----------------------------------------------------------------------
    # The update
    #----------------------------------------------------------------------
    return {"rewrite": best["text"], "status": status, "reason": reason, "log": [f"pick_best: round {best['round']} ({status})"]}
