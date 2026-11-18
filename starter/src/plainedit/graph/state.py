"""The state of the editing graph: what every node reads and writes."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Annotated, Any, TypedDict


#==========================================================================
# Reducers
#==========================================================================
def add_attempts(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Append new rewrite attempts to the list. Rounds must keep rising: a
    repeated or older round means a node ran twice and would double-count.

    Input:
        . left          : attempts so far (may be empty)
        . right         : attempts a node returns; each has an int "round"
    Output:
        . attempts      : left followed by right
    """
    # TODO T03 -- append the new attempts to the old ones; the rounds must keep rising:
    #     raise ValueError when an attempt's round is not after the last round so far.
    # CHECK: pytest -k t03 -- test_t03_add_attempts_*.
    raise NotImplementedError("T03: add_attempts")


#==========================================================================
# The log reducer
#==========================================================================
def add_log(left: list[str], right: list[str]) -> list[str]:
    """
    Append log lines; the log only ever grows.

    Input:
        . left          : lines so far (may be empty)
        . right         : lines a node returns
    Output:
        . log           : left followed by right
    """
    # TODO T03 -- append the new log lines to the old ones (the log only grows).
    # CHECK: pytest -k t03 -- test_t03_add_log_appends_lines and the two-node graph test.
    raise NotImplementedError("T03: add_log")


#==========================================================================
# The state
#==========================================================================
class EditState(TypedDict, total=False):
    """
    Purpose: everything one edit knows. attempts and log use reducers: a
    node returns only the NEW entries and the graph appends them. All other
    keys are replaced by what a node returns.
    """

    draft_id: str
    original: str                       # the notice as received
    declared_facts: list[str]           # facts the editor listed
    facts: list[str]                    # declared + found by code
    source_text: str                    # the notice without instruction-like sentences
    removed: list[str]                  # the instruction-like sentences taken out
    metrics_before: dict[str, Any]
    issues: list[str]                   # detected issue types: they drive the retrieval
    guidelines: list[dict[str, Any]]    # retrieved rules
    findings: list[dict[str, Any]]      # grounded findings
    attempts: Annotated[list[dict[str, Any]], add_attempts]
    rewrite: str
    feedback: list[str]                 # code feedback for the next rewrite
    passed: bool
    rounds: int
    status: str
    reason: str
    decision: dict[str, Any]
    log: Annotated[list[str], add_log]
