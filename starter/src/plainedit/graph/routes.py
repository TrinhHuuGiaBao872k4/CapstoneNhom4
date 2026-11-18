"""The conditional edge after check: pass, loop, or give up and pick the best."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    plainedit.graph.state           import  EditState


#==========================================================================
# After check
#==========================================================================
def after_check(state: EditState, *, max_rounds: int) -> str:
    """
    Choose the next node after check.

    Input:
        . state         : passed (bool) and rounds (rewrites done so far)
        . max_rounds    : the loop limit from the config
    Output:
        . name          : "editor_review" when the check passed; "write" when it
                          failed and rounds < max_rounds; "pick_best" when it failed
                          and the limit is reached
    """
    # TODO T04 -- return "editor_review" when state["passed"]; otherwise "write" while
    #     state["rounds"] < max_rounds, else "pick_best".
    # CHECK: pytest -k t04 -- test_t04_after_check_*.
    raise NotImplementedError("T04: after_check")
