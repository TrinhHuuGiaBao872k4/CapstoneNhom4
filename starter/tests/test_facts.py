"""checks/facts.py: what counts as the same fact, and what is missing."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  pytest

from    plainedit.checks.facts          import  canonical, extract_facts, merge_facts, missing_facts
from    plainedit.config                import  EditorConfig


#==========================================================================
# Same fact, other spelling
#==========================================================================
@pytest.mark.parametrize(
    ("fact", "rewrite"),
    [
        ("15 March 2027", "Pay by March 15, 2027 at the desk."),
        ("15 March 2027", "Pay by the 15th of March 2027."),
        ("15 March 2027", "Pay by 15 Mar 2027."),
        ("$45", "The fee is $45.00 only."),
        ("$45", "The fee is 45 dollars."),
        ("$1,200", "Pay $1200 today."),
        ("7:00 a.m.", "Come at 7:00 am sharp."),
        ("9:00 a.m.", "Come at 9 a.m."),
        ("5%", "A fee of 5 percent applies."),
        ("Room 204", "Go to room 204, please."),
        ("30 days", "You have 30 Days to reply."),
        ("Willow Street Library", "the willow street library opens"),
    ],
)
def test_same_fact_in_another_spelling_is_kept(fact: str, rewrite: str) -> None:
    """
    Pin the documented equivalences: dates, money, times, percent, case.

    Input:
        . fact          : the fact as written in the original
        . rewrite       : a rewrite that spells it differently
    """
    assert missing_facts([fact], rewrite) == []


#==========================================================================
# Different fact
#==========================================================================
@pytest.mark.parametrize(
    ("fact", "rewrite"),
    [
        ("15 March 2027", "Pay by 16 March 2027."),
        ("15 March 2027", "Pay by 15 March."),
        ("$45", "The fee is $54."),
        ("$45", "The fee is $450."),
        ("30 days", "You have thirty days."),
        ("30 days", "You have a 30-day window."),
        ("9:30 a.m.", "Come at 9 a.m."),
        ("Room 204", "Go to Room 24."),
    ],
)
def test_a_changed_or_respelled_fact_is_missing(fact: str, rewrite: str) -> None:
    """
    Pin the strict side: other numbers, spelled-out numbers, hyphenated units.

    Input:
        . fact          : the fact as written in the original
        . rewrite       : a rewrite that changes or respells it
    """
    assert missing_facts([fact], rewrite) == [fact]


#==========================================================================
# Missing facts keeps the order of the given list
#==========================================================================
def test_missing_facts_keeps_the_order_of_the_given_list() -> None:
    """
    Pin that only the lost facts come back, in the given order.
    """
    assert missing_facts(["$5", "Room 12", "1 May 2027"], "Room 12 is open.") == ["$5", "1 May 2027"]


#==========================================================================
# Canonical turns dates and money into tokens
#==========================================================================
def test_canonical_turns_dates_and_money_into_tokens() -> None:
    """
    Pin the canonical form used for comparison.
    """
    assert canonical("Due 15 March 2027, $45.00!") == "due date_2027_03_15 money_45_00"


#==========================================================================
# Finding facts
#==========================================================================
def test_extract_facts_finds_dates_money_times_and_units() -> None:
    """
    Pin extract_facts on one sentence with every kind of fact.
    """
    text  = "Pay $45 by 15 March 2027 at 9:00 a.m. within 30 days; the late fee is 5%."
    found = extract_facts(text, editor=EditorConfig())
    assert found == ["$45", "15 March 2027", "9:00 a.m.", "30 days", "5%"]


#==========================================================================
# Merge facts drops repeats with the same canonical form
#==========================================================================
def test_merge_facts_drops_repeats_with_the_same_canonical_form() -> None:
    """
    Pin that "$45" and "45 dollars" count once, declared facts first.
    """
    assert merge_facts(["Room 12", "$45"], ["45 dollars", "30 days"]) == ["Room 12", "$45", "30 days"]
