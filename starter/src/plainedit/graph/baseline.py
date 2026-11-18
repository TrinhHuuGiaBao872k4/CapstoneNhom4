"""Version v1: one generic prompt, one model call, no retrieval, critique, check or loop."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    langchain_core.runnables        import  RunnableConfig

from    plainedit.checks.facts          import  extract_facts, merge_facts, missing_facts
from    plainedit.checks.metrics        import  measure
from    plainedit.contract              import  EditResult
from    plainedit.graph.deps            import  Deps
from    plainedit.llm.rewrite           import  build_baseline_chain, clean_rewrite


#==========================================================================
# v1
#==========================================================================
def run_baseline(inputs: dict[str, Any], *, deps: Deps, run_config: RunnableConfig) -> EditResult:
    """
    Rewrite once with the generic prompt. The notice goes to the model as it
    is (no instruction guard) and nothing is checked: the contract reports
    what code measures, and the status is "approved" because v1 has no gate.

    Input:
        . inputs        : draft_id, text, facts
        . deps          : chat model, editor config, word swaps
        . run_config    : tags, metadata, callbacks
    Output:
        . result        : EditResult with no findings and rounds = 1
    """

    #----------------------------------------------------------------------
    # One generic rewrite
    #----------------------------------------------------------------------
    editor  = deps.config.editor
    text    = inputs["text"]
    rewrite = clean_rewrite(build_baseline_chain(deps.chat.get()).invoke({"draft": text}, run_config))

    #----------------------------------------------------------------------
    # The contract
    #----------------------------------------------------------------------
    facts   = merge_facts(inputs.get("facts", []), extract_facts(text, editor=editor))
    return EditResult(
        draft_id        = inputs["draft_id"],
        original        = text,
        rewrite         = rewrite,
        findings        = [],
        metrics_before  = measure(text, editor=editor, swaps=deps.swaps),
        metrics_after   = measure(rewrite, editor=editor, swaps=deps.swaps),
        facts_missing   = missing_facts(facts, rewrite),
        rounds          = 1,
        status          = "approved",
        reason          = "v1: one pass, no code check, scripted approval",
    )
