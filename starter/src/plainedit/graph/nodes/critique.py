"""Node critique (model + code): the model names problems, code keeps the grounded ones."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    plainedit.checks.metrics        import  normalize_words, split_sentences
from    plainedit.graph.deps            import  Deps
from    plainedit.graph.state           import  EditState
from    plainedit.llm.critique          import  build_critique_chain, format_guidelines


#==========================================================================
# Keep only grounded findings
#==========================================================================
def ground_findings(
    findings: list[dict[str, Any]], *, source: str, rule_ids: list[str], limit: int, quote_words: int = 12
) -> tuple[list[dict[str, Any]], int]:
    """
    A finding is grounded when its quote is a substring of the notice (case,
    punctuation and spacing ignored) and its rule number points at one of the
    retrieved rules (1 .. len(rule_ids)). Everything else is dropped and
    counted. A grounded quote is cut to its first quote_words words.

    Input:
        . findings      : the model's findings as dicts (issue, quote, rule)
        . source        : the notice the model read
        . rule_ids      : rule ids that were retrieved, in the order the prompt numbered them
        . limit         : at most this many findings are kept
        . quote_words   : the longest quote kept
    Output:
        . kept          : {issue, quote, rule_id} dicts, in order, at most `limit`
        . dropped       : how many of the model's findings were ungrounded
    """
    haystack = f" {normalize_words(source)} "
    kept     = [
        {"issue": item["issue"], "quote": " ".join(item["quote"].split()[:quote_words]), "rule_id": rule_ids[item["rule"] - 1]}
        for item in findings
        if normalize_words(item["quote"]) and f" {normalize_words(item['quote'])} " in haystack
        and 1 <= item["rule"] <= len(rule_ids)
    ]
    return kept[:limit], len(findings) - len(kept)


#==========================================================================
# critique
#==========================================================================
def critique_node(state: EditState, *, deps: Deps) -> dict[str, Any]:
    """
    Ask the model for findings, with the retrieved rules as context. With no
    detected issue there is nothing to critique and no model call is made.
    A reply that is not valid structured output gives no findings and says so
    in the log; the rewrite still runs.

    Input:
        . state         : source_text, issues, guidelines
        . deps          : chat model, editor config
    Output:
        . update        : findings, log
    """

    #----------------------------------------------------------------------
    # Nothing detected: no model call
    #----------------------------------------------------------------------
    if not state["guidelines"]:
        return {"findings": [], "log": ["critique: no rule retrieved, model not called"]}

    #----------------------------------------------------------------------
    # Ask the model; invalid structured output is a visible, logged outcome
    #----------------------------------------------------------------------
    editor    = deps.config.editor
    sentences = split_sentences(state["source_text"], editor=editor)
    chain     = build_critique_chain(deps.chat.get())
    try:
        critique = chain.invoke({
            "guidelines": format_guidelines(state["guidelines"], words=30),
            "issues": ", ".join(state["issues"]),
            "draft": "\n".join(f"{number}. {sentence}" for number, sentence in enumerate(sentences, 1)),
        })
    except ValueError as error:
        return {"findings": [], "log": [f"critique: invalid model output ({type(error).__name__}), no findings"]}
    if critique is None:
        return {"findings": [], "log": ["critique: the model made no structured reply, no findings"]}

    #----------------------------------------------------------------------
    # Keep the grounded findings
    #----------------------------------------------------------------------
    raw           = [finding.model_dump() for finding in critique.findings]
    kept, dropped = ground_findings(
        raw,
        source      = state["source_text"],
        rule_ids    = [rule["rule_id"] for rule in state["guidelines"]],
        limit       = editor.max_findings,
    )
    return {"findings": kept, "log": [f"critique: {len(raw)} finding(s) from the model, {len(kept)} kept, {dropped} dropped as ungrounded"]}
