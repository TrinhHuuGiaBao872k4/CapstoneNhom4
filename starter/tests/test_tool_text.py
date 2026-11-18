"""llm/tool_text.py: what a small model writes around a tool call is read, not trusted blindly."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    plainedit.llm.tool_text         import  parse_tool_calls


#==========================================================================
# A clean call
#==========================================================================
def test_a_clean_tool_call_is_parsed_and_removed_from_the_text() -> None:
    """
    Pin the normal case: <tool_call>{json}</tool_call> becomes one call and leaves the text empty.
    """
    content, calls = parse_tool_calls('<tool_call>\n{"name": "Critique", "arguments": {"findings": []}}\n</tool_call>')
    assert content == "" and calls[0]["name"] == "Critique" and calls[0]["args"] == {"findings": []}


#==========================================================================
# What the 1.5B model really does
#==========================================================================
def test_a_missing_closing_tag_and_rambling_after_the_json_are_tolerated() -> None:
    """
    Pin the real case seen on D03: the JSON is complete but the closing tag
    never comes and the model goes on talking.
    """
    text = '<tool_call>\n{"name": "Critique", "arguments": {"findings": [{"issue": "shall", "quote": "a", "rule": 1}]}}\n\nThe code has identified issues:\n1. ...'
    content, calls = parse_tool_calls(text)
    assert calls[0]["args"]["findings"][0]["rule"] == 1
    assert content.startswith("The code has identified issues")


#==========================================================================
# One missing closing brace is repaired when the closing tag follows
#==========================================================================
def test_one_missing_closing_brace_is_repaired_when_the_closing_tag_follows() -> None:
    """
    Pin the real case seen on D08: the last } is missing but </tool_call> is there.
    """
    text = '<tool_call>\n{"name": "Critique", "arguments": {"findings": [{"issue": "shall", "quote": "a", "rule": 1}]} \n</tool_call>'
    content, calls = parse_tool_calls(text)
    assert calls and calls[0]["args"]["findings"][0]["issue"] == "shall" and content == ""


#==========================================================================
# An unreadable call stays in the text
#==========================================================================
def test_an_unreadable_call_stays_in_the_text() -> None:
    """
    Pin that garbage is not repaired: no closing tag and no JSON means no call and the text is kept.
    """
    text = "<tool_call>\nnot json at all"
    content, calls = parse_tool_calls(text)
    assert calls == [] and "not json" in content
