"""Run the graph: start, wait at the interrupt, resume, read the contract."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    langchain_core.runnables        import  RunnableConfig
from    langgraph.types                 import  Command

from    plainedit.checks.facts          import  missing_facts
from    plainedit.checks.metrics        import  measure
from    plainedit.contract              import  EditResult
from    plainedit.graph.deps            import  Deps


#==========================================================================
# Start an edit
#==========================================================================
def start_edit(
    graph: Any, *, draft_id: str, text: str, facts: list[str], thread_id: str, run_config: RunnableConfig
) -> None:
    """
    Run the graph on one notice until it stops at the editor interrupt.

    Input:
        . graph         : from build_graph
        . draft_id      : an id for the contract
        . text          : the notice
        . facts         : facts the editor declares (code finds more)
        . thread_id     : the checkpoint thread; use it to resume
        . run_config    : tags, metadata, callbacks from run_config()
    """
    config = {**run_config, "configurable": {"thread_id": thread_id}}
    graph.invoke({"draft_id": draft_id, "original": text, "declared_facts": facts}, config)


#==========================================================================
# Resume an edit
#==========================================================================
def resume_edit(graph: Any, *, thread_id: str, decision: dict[str, Any], run_config: RunnableConfig) -> None:
    """
    Continue a waiting thread with the editor's decision. Works in a NEW
    process: the thread's state is read from the checkpoint database.

    Input:
        . graph         : from build_graph (same checkpointer file)
        . thread_id     : the thread printed by ask
        . decision      : {"action": "approve" | "edit" | "reject", "text": ..., "note": ...}
        . run_config    : tags, metadata, callbacks
    """
    config = {**run_config, "configurable": {"thread_id": thread_id}}
    graph.invoke(Command(resume=decision), config)


#==========================================================================
# Read the thread
#==========================================================================
def read_thread(graph: Any, thread_id: str) -> tuple[dict[str, Any], bool]:
    """
    Read the state of a thread.

    Input:
        . graph         : from build_graph
        . thread_id     : the thread id
    Output:
        . values        : the state values ({} for an unknown thread)
        . waiting       : True when the graph is stopped at the editor interrupt
    """
    snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
    return dict(snapshot.values), "editor_review" in snapshot.next


#==========================================================================
# The contract
#==========================================================================
def build_result(values: dict[str, Any], *, waiting: bool, deps: Deps) -> EditResult:
    """
    Make the typed contract from the graph state. While the graph waits for
    the editor the status is needs_editor; metrics_after and facts_missing are
    always recomputed by code from the current rewrite.

    Input:
        . values        : state values of the thread
        . waiting       : True when stopped at the interrupt
        . deps          : editor config, word swaps
    Output:
        . result        : EditResult; call .to_contract() for the JSON dict
    """

    #----------------------------------------------------------------------
    # Status while waiting or after the decision
    #----------------------------------------------------------------------
    rewrite = values["rewrite"]
    if waiting:
        previous = values.get("reason", "")
        status, reason = "needs_editor", "waiting for the editor" + (f" ({previous})" if previous else "")
    else:
        status, reason = values["status"], values["reason"]

    #----------------------------------------------------------------------
    # The contract
    #----------------------------------------------------------------------
    return EditResult(
        draft_id        = values["draft_id"],
        original        = values["original"],
        rewrite         = rewrite,
        findings        = values["findings"],
        metrics_before  = values["metrics_before"],
        metrics_after   = measure(rewrite, editor=deps.config.editor, swaps=deps.swaps),
        facts_missing   = missing_facts(values["facts"], rewrite),
        rounds          = values["rounds"],
        status          = status,
        reason          = reason,
    )
