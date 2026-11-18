"""Build the run config that connects a call to a tracer, with labels."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    langchain_core.callbacks        import  BaseCallbackHandler
from    langchain_core.runnables        import  RunnableConfig

from    plainedit.config                import  TracingConfig


#==========================================================================
# Run config
#==========================================================================
def run_config(
    tracing: TracingConfig,
    *,
    tracer: BaseCallbackHandler | None = None,
    run_name: str | None = None,
    metadata: dict[str, Any] | None = None,
    extra_tags: tuple[str, ...] = (),
) -> RunnableConfig:
    """
    Pass the tracer as a callback; tags and metadata make the run findable
    later, locally and on LangSmith (where they become filters).

    Input:
        . tracing       : the project's tags
        . tracer        : a LocalTracer, or None (LangSmith alone needs none)
        . run_name      : name of the root run, or None
        . metadata      : e.g. {"version": "v2", "case_id": "D07"}
        . extra_tags    : tags for this call only
    Output:
        . config        : the config argument of invoke / stream
    """
    config: RunnableConfig = {
        "tags": [*tracing.tags, *extra_tags],
        "metadata": dict(metadata or {}),
    }
    if tracer is not None:
        config["callbacks"] = [tracer]
    if run_name:
        config["run_name"] = run_name
    return config


#==========================================================================
# Run config of one case
#==========================================================================
def case_config(
    tracing: TracingConfig,
    *,
    version: str,
    case_id: str,
    backend: str,
    tracer: BaseCallbackHandler | None = None,
) -> RunnableConfig:
    """
    Label one run of a version on one case: the tag is the version, the
    metadata holds version, case_id and backend, the root run is named
    "edit-<case_id>". Filter by these on LangSmith or in a local trace.

    Input:
        . tracing       : the project's tags
        . version       : "v1", "v2", "ask", ...
        . case_id       : the draft or case id
        . backend       : "local", "server" or "fake"
        . tracer        : a LocalTracer, or None
    Output:
        . config        : the config argument of invoke
    """
    # TODO T07 -- return run_config(...) with the tracer, run_name f"edit-{case_id}", metadata {"version", "case_id", "backend"}
    #     and the version as one extra tag.
    # CHECK: pytest -k t07 -- test_t07_case_config_*.
    raise NotImplementedError("T07: case_config")
