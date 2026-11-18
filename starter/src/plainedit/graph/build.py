"""Wire the nodes into the LangGraph graph."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    functools                       import  partial
from    typing                          import  Any

from    langgraph.checkpoint.base       import  BaseCheckpointSaver
from    langgraph.graph                 import  END, START, StateGraph

from    plainedit.graph.deps                 import  Deps
from    plainedit.graph.nodes.check          import  check_node
from    plainedit.graph.nodes.critique       import  critique_node
from    plainedit.graph.nodes.editor_review  import  editor_review
from    plainedit.graph.nodes.measure        import  measure_node
from    plainedit.graph.nodes.pick_best      import  pick_best_node
from    plainedit.graph.nodes.publish        import  publish_node
from    plainedit.graph.nodes.retrieve       import  retrieve_node
from    plainedit.graph.nodes.rewrite        import  rewrite_node
from    plainedit.graph.routes               import  after_check
from    plainedit.graph.state                import  EditState


#==========================================================================
# Build the graph
#==========================================================================
def build_graph(deps: Deps, *, checkpointer: BaseCheckpointSaver) -> Any:
    """
    START -> measure -> retrieve -> critique -> write -> check
    check -> editor_review (pass) | write (fail, rounds < max) | pick_best (fail, limit)
    pick_best -> editor_review -> publish -> END.
    The node is called "write" because "rewrite" is a state key.

    Input:
        . deps          : config, chat, store, swaps, published path
        . checkpointer  : required: editor_review interrupts and resumes
    Output:
        . graph         : a compiled graph; invoke with a thread_id in config.configurable
    """

    #----------------------------------------------------------------------
    # The nodes
    #----------------------------------------------------------------------
    graph = StateGraph(EditState)
    graph.add_node("measure", partial(measure_node, deps=deps))
    graph.add_node("retrieve", partial(retrieve_node, deps=deps))
    graph.add_node("critique", partial(critique_node, deps=deps))
    graph.add_node("write", partial(rewrite_node, deps=deps))
    graph.add_node("check", partial(check_node, deps=deps))
    graph.add_node("pick_best", pick_best_node)
    graph.add_node("editor_review", partial(editor_review, deps=deps))
    graph.add_node("publish", partial(publish_node, deps=deps))

    #----------------------------------------------------------------------
    # The edges
    #----------------------------------------------------------------------
    graph.add_edge(START, "measure")
    graph.add_edge("measure", "retrieve")
    graph.add_edge("retrieve", "critique")
    graph.add_edge("critique", "write")
    graph.add_edge("write", "check")
    graph.add_conditional_edges(
        "check",
        partial(after_check, max_rounds=deps.config.editor.max_rounds),
        {"editor_review": "editor_review", "write": "write", "pick_best": "pick_best"},
    )
    graph.add_edge("pick_best", "editor_review")
    graph.add_edge("editor_review", "publish")
    graph.add_edge("publish", END)
    return graph.compile(checkpointer=checkpointer)
