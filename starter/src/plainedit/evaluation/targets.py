"""The apps under test: v1 (one pass) and v2 (the graph), as target functions."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  sys
import  time
from    pathlib                         import  Path
from    typing                          import  Any

from    langgraph.checkpoint.memory     import  InMemorySaver

from    plainedit.graph.baseline              import  run_baseline
from    plainedit.graph.build                 import  build_graph
from    plainedit.graph.deps                  import  Deps
from    plainedit.graph.run                   import  build_result, read_thread, resume_edit, start_edit
from    plainedit.observability.local_tracer  import  LocalTracer
from    plainedit.observability.trace_config  import  case_config
from    plainedit.observability.trace_view    import  save_trace


#==========================================================================
# One version as a target
#==========================================================================
class EditTarget:
    """
    Purpose: call it with a case's inputs, get the contract dict. v2 runs
    the graph and answers the editor interrupt with a scripted "approve";
    v1 runs one prompt. Each case saves a local trace to
    runtime/traces/eval-<version>-<case>.json.
    """

    #----------------------------------------------------------------------
    # Keep the version and its dependencies
    #----------------------------------------------------------------------
    def __init__(self, version: str, deps: Deps, *, trace_dir: Path | None) -> None:
        """
        Prepare the target; v2 compiles the graph with an in-memory checkpointer.

        Input:
            . version       : "v1" or "v2"
            . deps          : config, chat, store, swaps, published path
            . trace_dir     : where each case's trace is saved, or None
        """
        if version not in ("v1", "v2"):
            raise ValueError(f"version must be v1 or v2, got {version!r}")
        self._version   = version
        self._deps      = deps
        self._trace_dir = trace_dir
        self._graph     = build_graph(deps, checkpointer=InMemorySaver()) if version == "v2" else None

    #----------------------------------------------------------------------
    # Run one case
    #----------------------------------------------------------------------
    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Edit one notice and return the contract.

        Input:
            . inputs        : draft_id, text, facts
        Output:
            . contract      : the EditResult as a dict
        """

        #------------------------------------------------------------------
        # Label the run
        #------------------------------------------------------------------
        deps    = self._deps
        case_id = inputs["draft_id"]
        tracer  = LocalTracer()
        run_cfg = case_config(
            deps.config.tracing, version=self._version, case_id=case_id,
            backend=deps.config.model.backend, tracer=tracer,
        )

        #------------------------------------------------------------------
        # Run v1 or v2 and keep the trace
        #------------------------------------------------------------------
        started = time.perf_counter()
        try:
            if self._graph is None:
                result = run_baseline(inputs, deps=deps, run_config=run_cfg)
            else:
                thread = f"{self._version}-{case_id}"
                start_edit(
                    self._graph, draft_id=case_id, text=inputs["text"], facts=inputs.get("facts", []),
                    thread_id=thread, run_config=run_cfg,
                )
                resume_edit(self._graph, thread_id=thread, decision={"action": "approve"}, run_config=run_cfg)
                values, waiting = read_thread(self._graph, thread)
                result = build_result(values, waiting=waiting, deps=deps)
        finally:
            if self._trace_dir is not None:
                save_trace(tracer, self._trace_dir / f"eval-{self._version}-{case_id}.json")
        print(f"[{self._version}] {case_id} {time.perf_counter() - started:.0f}s", file=sys.stderr, flush=True)
        return result.to_contract()
