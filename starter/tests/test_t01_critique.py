"""T01 (LangChain): the guideline context and the critique chain; plus the grounding filter."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    pathlib                         import  Path

from    helpers                         import  plain_deps
from    plainedit.graph.nodes.critique  import  critique_node, ground_findings
from    plainedit.llm.critique          import  Critique, build_critique_chain, format_guidelines
from    plainedit.llm.fake_chat_model   import  FakeChatModel
from    plainedit.llm.fake_rules        import  project_fake_rules


#==========================================================================
# T01: format_guidelines
#==========================================================================
def test_t01_format_guidelines_numbers_cuts_and_labels() -> None:
    """
    Pin T01: one numbered line per rule with its title and issue, the text
    cut to `words` words; an empty list gives "(none)".
    """
    rules = [
        {"rule_id": "a/one", "title": "Use active voice", "issue": "passive", "text": "alpha beta gamma delta"},
        {"rule_id": "b/two", "title": "Use must", "issue": "shall", "text": "one two"},
    ]
    lines = format_guidelines(rules, words=3).splitlines()
    assert lines == ["1. Use active voice (for passive): alpha beta gamma", "2. Use must (for shall): one two"]
    assert format_guidelines([]) == "(none)"


#==========================================================================
# T01: the chain
#==========================================================================
def test_t01_critique_chain_returns_a_critique_from_the_fake_model() -> None:
    """
    Pin T01: prompt | structured output returns a Critique object (no download).
    """
    chain = build_critique_chain(FakeChatModel(rules=project_fake_rules()))
    out   = chain.invoke({
        "guidelines": "1. Use active voice (for passive): x",
        "issues": "passive",
        "draft": "1. Applications shall be submitted by Friday.",
    })
    assert isinstance(out, Critique)
    assert out.findings[0].issue == "passive" and out.findings[0].quote == "Applications shall be submitted by"


#==========================================================================
# T01: the node that uses the chain
#==========================================================================
def test_t01_critique_node_keeps_the_grounded_finding_and_counts_the_dropped(tmp_path: Path) -> None:
    """
    Pin the critique node on the fake model: one grounded finding is kept,
    the invented one is dropped and counted in the log; no rule retrieved
    means no model call.

    Input:
        . tmp_path      : temporary folder for the deps
    """
    deps  = plain_deps(tmp_path)
    rules = [{"rule_id": "conversational/use-active-voice", "title": "Use active voice", "issue": "passive", "text": "Use active voice."}]
    state = {"source_text": "Applications shall be submitted by Friday.", "issues": ["passive"], "guidelines": rules}
    out   = critique_node(state, deps=deps)
    assert out["findings"] == [{"issue": "passive", "quote": "Applications shall be submitted by", "rule_id": "conversational/use-active-voice"}]
    assert "1 dropped as ungrounded" in out["log"][0]
    empty = critique_node({**state, "guidelines": []}, deps=deps)
    assert empty["findings"] == [] and "model not called" in empty["log"][0]


#==========================================================================
# The grounding filter (given)
#==========================================================================
def test_ground_findings_needs_a_quote_in_the_notice_and_a_numbered_rule() -> None:
    """
    Pin the filter: quote must be in the notice (case and punctuation ignored)
    and the rule number must exist; the quote is cut to 12 words; limit applies.
    """
    source   = "Applications SHALL be submitted, in writing, by Friday. Fees are due."
    findings = [
        {"issue": "shall", "quote": "applications shall be submitted in writing", "rule": 1},
        {"issue": "passive", "quote": "A sentence that is not there", "rule": 1},
        {"issue": "passive", "quote": "Fees are due", "rule": 7},
        {"issue": "passive", "quote": "Fees are due.", "rule": 2},
    ]
    kept, dropped = ground_findings(findings, source=source, rule_ids=["x/a", "x/b"], limit=4)
    assert [item["rule_id"] for item in kept] == ["x/a", "x/b"] and dropped == 2
    assert ground_findings(findings, source=source, rule_ids=["x/a", "x/b"], limit=1)[0] == kept[:1]
    long_quote = [{"issue": "shall", "quote": "Applications SHALL be submitted, in writing, by Friday.", "rule": 1}]
    assert len(ground_findings(long_quote, source=source, rule_ids=["x/a"], limit=4, quote_words=4)[0][0]["quote"].split()) == 4


#==========================================================================
# A quote cut in the middle of a date is still grounded
#==========================================================================
def test_ground_findings_compares_plain_words_not_dates() -> None:
    """
    Pin the real bug found on D12: a quote cut after "9 September" (the year
    left out) is still words of the notice; comparing it as a "date" token
    would call it ungrounded.
    """
    source = "The council meets on 9 September 2027 at 7:00 p.m. in the hall."
    quote  = "The council meets on 9 September"
    kept, dropped = ground_findings([{"issue": "passive", "quote": quote, "rule": 1}], source=source, rule_ids=["x/a"], limit=4)
    assert len(kept) == 1 and dropped == 0
