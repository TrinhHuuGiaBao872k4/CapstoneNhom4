"""Node rewrite (model): write the plain version, with code feedback from round 2."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    plainedit.graph.deps            import  Deps
from    plainedit.graph.state           import  EditState
from    plainedit.llm.critique          import  format_guidelines
from    plainedit.llm.rewrite           import  build_rewrite_chain, clean_rewrite


#==========================================================================
# rewrite
#==========================================================================
def rewrite_node(state: EditState, *, deps: Deps) -> dict[str, Any]:
    """
    Rewrite the notice with the guidelines, the findings, the facts to keep
    and (round 2 and later) the exact feedback of the last code check.

    Input:
        . state         : source_text, guidelines, findings, facts, feedback, rounds
        . deps          : chat model
    Output:
        . update        : rewrite, rounds (+1), log
    """

    #----------------------------------------------------------------------
    # Findings and feedback as text
    #----------------------------------------------------------------------
    findings = "\n".join(f"- {item['issue']}: \"{item['quote']}\"" for item in state["findings"]) or "(none)"
    feedback = ""
    if state.get("feedback"):
        feedback = "\nYour last attempt failed the code check. Fix every line:\n" + "\n".join(
            f"- {line}" for line in state["feedback"]
        ) + "\n"

    #----------------------------------------------------------------------
    # Rewrite
    #----------------------------------------------------------------------
    text = build_rewrite_chain(deps.chat.get()).invoke({
        "guidelines": format_guidelines(state["guidelines"], words=30),
        "findings": findings,
        "facts": "\n".join(f"- {fact}" for fact in state["facts"]) or "(none)",
        "feedback": feedback,
        "draft": state["source_text"],
    })
    rounds = state["rounds"] + 1
    return {
        "rewrite": clean_rewrite(text),
        "rounds": rounds,
        "log": [f"rewrite: round {rounds}{' with code feedback' if feedback else ''}"],
    }
