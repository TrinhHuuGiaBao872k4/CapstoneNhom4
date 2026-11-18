"""Compare the code slice and the Langflow flow on the same guideline questions."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any


#==========================================================================
# Compare answers
#==========================================================================
def compare_answers(
    questions: list[dict[str, Any]],
    code_answers: list[str],
    flow_answers: list[str],
) -> list[dict[str, Any]]:
    """
    Judge each pair of answers with a plain code rule: an answer is OK when
    it contains at least one of the question's expect_any words (any case).
    The verdict says who got it: both, code_only, flow_only or neither.

    Input:
        . questions     : rows with id and expect_any (list of words)
        . code_answers  : the code slice's answers, same order
        . flow_answers  : the flow's answers, same order
    Output:
        . rows          : {id, code_ok, flow_ok, verdict} per question
    """
    # TODO T08 -- for each question (zip the three lists, strict): code_ok / flow_ok = any expect_any word is in the lower-cased answer;
    #     verdict "both", "code_only", "flow_only" or "neither"; row {id, code_ok, flow_ok, verdict}.
    # CHECK: pytest -k t08 -- test_t08_compare_answers_*.
    raise NotImplementedError("T08: compare_answers")
