"""The JSON contract of one edit: what python main.py ask prints."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any, Literal

from    pydantic                        import  BaseModel


#==========================================================================
# One finding of the critique
#==========================================================================
class FindingOut(BaseModel):
    """
    Purpose: one grounded finding as it appears in the contract: the issue
    type, the exact words of the notice, and the guideline that applies.
    """

    issue: str
    quote: str
    rule_id: str


#==========================================================================
# The result of one edit
#==========================================================================
class EditResult(BaseModel):
    """
    Purpose: the typed result of one edit. status is approved (an editor
    signed off and no fact is missing), needs_editor (a human must act: the
    graph is waiting, or no attempt kept every fact) or rejected.
    """

    draft_id: str
    original: str
    rewrite: str
    findings: list[FindingOut]
    metrics_before: dict[str, Any]
    metrics_after: dict[str, Any]
    facts_missing: list[str]
    rounds: int
    status: Literal["approved", "needs_editor", "rejected"]
    reason: str

    #----------------------------------------------------------------------
    # Plain dictionary for printing and saving
    #----------------------------------------------------------------------
    def to_contract(self) -> dict[str, Any]:
        """
        Dump the result in the key order of the contract.

        Output:
            . contract      : draft_id, original, rewrite, findings, metrics_before,
                              metrics_after, facts_missing, rounds, status, reason
        """
        return self.model_dump()
