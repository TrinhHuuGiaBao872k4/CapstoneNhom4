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
    rows: list[dict[str, Any]] = []
    for question, code, flow in zip(questions, code_answers, flow_answers, strict=True):
        expect  = [word.lower() for word in question["expect_any"]]
        code_ok = any(word in code.lower() for word in expect)
        flow_ok = any(word in flow.lower() for word in expect)
        if code_ok and flow_ok:
            verdict = "both"
        elif code_ok:
            verdict = "code_only"
        elif flow_ok:
            verdict = "flow_only"
        else:
            verdict = "neither"
        rows.append({"id": question["id"], "code_ok": code_ok, "flow_ok": flow_ok, "verdict": verdict})
    return rows
