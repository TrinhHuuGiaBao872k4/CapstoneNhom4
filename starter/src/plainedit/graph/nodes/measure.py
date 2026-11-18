"""Node measure (code): clean the notice, measure it, find the issue types."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    plainedit.checks.facts          import  extract_facts, merge_facts
from    plainedit.checks.guard          import  strip_instructions
from    plainedit.checks.metrics        import  detected_issues, find_issues, measure
from    plainedit.graph.deps            import  Deps
from    plainedit.graph.state           import  EditState


#==========================================================================
# measure
#==========================================================================
def measure_node(state: EditState, *, deps: Deps) -> dict[str, Any]:
    """
    Take instruction-like sentences out of the notice, join the editor's facts
    with the facts code finds, measure the notice and list its issue types.

    Input:
        . state         : original, declared_facts
        . deps          : editor config, word swaps
    Output:
        . update        : source_text, removed, facts, metrics_before, issues, rounds, log
    """

    #----------------------------------------------------------------------
    # Clean and measure the notice
    #----------------------------------------------------------------------
    editor        = deps.config.editor
    clean, removed = strip_instructions(state["original"], editor=editor)
    facts         = merge_facts(state.get("declared_facts", []), extract_facts(clean, editor=editor))
    metrics       = measure(clean, editor=editor, swaps=deps.swaps)
    issues        = detected_issues(find_issues(clean, editor=editor, swaps=deps.swaps), editor=editor)

    #----------------------------------------------------------------------
    # The update
    #----------------------------------------------------------------------
    return {
        "source_text": clean,
        "removed": removed,
        "facts": facts,
        "metrics_before": metrics,
        "issues": issues,
        "rounds": 0,
        "log": [
            f"measure: issue_score {metrics['issue_score']}, issues {issues}, {len(facts)} facts, "
            f"{len(removed)} instruction-like sentence(s) removed"
        ],
    }
