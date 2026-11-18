"""Node retrieve (vector DB): the guideline rules for the detected issues."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    plainedit.graph.deps                  import  Deps
from    plainedit.graph.state                 import  EditState
from    plainedit.knowledge.guideline_search  import  find_rules


#==========================================================================
# retrieve
#==========================================================================
def retrieve_node(state: EditState, *, deps: Deps) -> dict[str, Any]:
    """
    Search the guideline collection once per detected issue type.

    Input:
        . state         : issues
        . deps          : the store and the retrieval config
    Output:
        . update        : guidelines, log
    """
    rules = find_rules(deps.store, state["issues"], retrieval=deps.config.retrieval)
    return {"guidelines": rules, "log": [f"retrieve: {len(rules)} rule(s) {[rule['rule_id'] for rule in rules]}"]}
