"""Node publish (code): append an approved rewrite to a file, once per thread."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
from    typing                          import  Any

from    langchain_core.runnables        import  RunnableConfig

from    plainedit.graph.deps            import  Deps
from    plainedit.graph.state           import  EditState


#==========================================================================
# publish
#==========================================================================
def publish_node(state: EditState, config: RunnableConfig, *, deps: Deps) -> dict[str, Any]:
    """
    Write one line to the published file for an approved edit. The thread id
    is the key: running the node again for the same thread writes nothing.

    Input:
        . state         : status, draft_id, rewrite, reason
        . config        : LangGraph injects it; configurable.thread_id is the key
        . deps          : published_path
    Output:
        . update        : log
    """
    if state["status"] != "approved":
        return {"log": [f"publish: nothing published, status is {state['status']}"]}
    thread_id = config["configurable"]["thread_id"]
    path      = deps.published_path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines     = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    if any(json.loads(line)["thread_id"] == thread_id for line in lines):
        return {"log": ["publish: already published for this thread, skipped"]}
    record = {"thread_id": thread_id, "draft_id": state["draft_id"], "rewrite": state["rewrite"], "reason": state["reason"]}
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"log": ["publish: written"]}
