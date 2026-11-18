"""Facts: find them in a notice and check that a rewrite still has every one.

WHAT COUNTS AS THE SAME FACT (strict and simple, on purpose):
  . dates      "15 March 2027" = "March 15, 2027" = "15 Mar 2027" (a missing year matches a missing year only)
  . times      "9:00 a.m." = "9:00 am" = "9 a.m."; "9:30 a.m." is a different fact
  . money      "$45" = "$45.00" = "45 dollars"; "$1,200" = "$1200"
  . percent    "5%" = "5 percent"
  . anything else (names, rooms, "30 days"): the same words, any case, any
    punctuation; hyphens count as spaces ("30-day" is NOT "30 days")
Spelled-out numbers ("thirty days") are NOT the same fact: the editor prompt
tells the model to copy facts exactly, and the check holds it to that.
"""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  re

from    plainedit.config                import  EditorConfig


#==========================================================================
# Month names
#==========================================================================
def month_number(name: str) -> int:
    """
    Turn an English month name or its three-letter form into 1..12.

    Input:
        . name          : "March", "Mar", "sept"
    Output:
        . number        : 1 for January ... 12 for December
    """
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    return months.index(name.lower()[:3]) + 1


#==========================================================================
# Canonical form of a text
#==========================================================================
def canonical(text: str) -> str:
    """
    Rewrite dates, times, money and percentages as one token each, then
    lower-case the text and turn every other punctuation into a space.

    Input:
        . text          : a fact or a whole rewrite
    Output:
        . canon         : lower-case words and tokens like date_2027_03_15, money_45_00
    """

    #----------------------------------------------------------------------
    # Dates, times, money, percent become single tokens
    #----------------------------------------------------------------------
    month = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    text  = text.replace(" ", " ")
    text  = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)
    text  = re.sub(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{month}\b\.?(?:,?\s+(\d{{4}}))?",
        lambda m: _date_token(m.group(3), m.group(2), m.group(1)), text, flags=re.IGNORECASE,
    )
    text  = re.sub(
        rf"\b{month}\b\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(\d{{4}}))?",
        lambda m: _date_token(m.group(3), m.group(1), m.group(2)), text, flags=re.IGNORECASE,
    )
    text  = re.sub(
        r"\b(\d{1,2})(?::(\d{2}))?\s?([ap])\.?m\b\.?",
        lambda m: f" time_{int(m.group(1))}_{m.group(2) or '00'}_{m.group(3).lower()} ", text, flags=re.IGNORECASE,
    )
    text  = re.sub(r"\$\s?(\d+)(?:\.(\d{1,2}))?", lambda m: _money_token(m.group(1), m.group(2)), text)
    text  = re.sub(
        r"\b(\d+)(?:\.(\d{1,2}))?\s+(?:dollars?|usd)\b", lambda m: _money_token(m.group(1), m.group(2)), text,
        flags=re.IGNORECASE,
    )
    text  = re.sub(
        r"\b(\d+)\s?(?:%|percent|per cent)", lambda m: f" pct_{m.group(1)} ", text, flags=re.IGNORECASE
    )

    #----------------------------------------------------------------------
    # Everything else: lower-case words
    #----------------------------------------------------------------------
    return " ".join(re.sub(r"[^\w]+", " ", text.lower()).split())


#==========================================================================
# Tokens
#==========================================================================
def _date_token(year: str | None, month: str, day: str) -> str:
    """
    Write one date as a token; no year gives "xxxx".

    Input:
        . year          : "2027" or None
        . month         : month name
        . day           : day of month
    Output:
        . token         : e.g. " date_2027_03_15 "
    """
    return f" date_{year or 'xxxx'}_{month_number(month):02d}_{int(day):02d} "


#==========================================================================
#  money token
#==========================================================================
def _money_token(dollars: str, cents: str | None) -> str:
    """
    Write one amount as a token; "$45" and "$45.00" give the same one.

    Input:
        . dollars       : digits before the point
        . cents         : digits after the point, or None
    Output:
        . token         : e.g. " money_45_00 "
    """
    return f" money_{int(dollars)}_{(cents or '0').ljust(2, '0')} "


#==========================================================================
# Which facts are missing
#==========================================================================
def missing_facts(facts: list[str], rewrite: str) -> list[str]:
    """
    Return the facts that do not appear in the rewrite (same words in the
    same order, as in the module docstring).

    Input:
        . facts         : facts as written in the original, e.g. ["15 March 2027", "$45"]
        . rewrite       : the text to check
    Output:
        . missing       : the facts not found, in the given order; [] = nothing lost
    """
    haystack = f" {canonical(rewrite)} "
    return [fact for fact in facts if f" {canonical(fact)} " not in haystack]


#==========================================================================
# Find facts in a text
#==========================================================================
def extract_facts(text: str, *, editor: EditorConfig) -> list[str]:
    """
    Find dates, times, money, percentages and "number unit" pairs in a text,
    exactly as written. The editor's own list of facts is added to these by
    the measure node; names and rooms need the editor's list.

    Input:
        . text          : the original notice
        . editor        : fact_units
    Output:
        . facts         : found strings, first occurrence order, no repeats
    """
    month    = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    units    = "|".join(sorted(editor.fact_units, key=len, reverse=True))
    patterns = [
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{month}\b\.?(?:,?\s+\d{{4}})?",
        rf"\b{month}\b\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\b(?:,?\s+\d{{4}})?",
        r"\b\d{1,2}(?::\d{2})?\s?[ap]\.?m\b\.?",
        r"\$\s?\d[\d,]*(?:\.\d{1,2})?",
        r"\b\d+\s?(?:%|percent)",
        rf"\b\d+\s+(?:{units})\b",
    ]
    found: list[tuple[int, str]] = []
    for pattern in patterns:
        found += [(match.start(), _trim(match.group(0))) for match in re.finditer(pattern, text, re.IGNORECASE)]
    return merge_facts([], [fact for _, fact in sorted(found)])


#==========================================================================
# Trim a found fact
#==========================================================================
def _trim(fact: str) -> str:
    """
    Remove spaces, commas and a sentence-ending dot around a found fact, but
    keep the dot of "a.m." and "p.m.".

    Input:
        . fact          : the matched text
    Output:
        . fact          : the fact as it should be written back
    """
    fact = fact.strip(" ,")
    if fact.endswith(".") and not re.search(r"[ap]\.m\.$", fact, re.IGNORECASE):
        fact = fact.rstrip(".")
    return fact


#==========================================================================
# Merge two fact lists
#==========================================================================
def merge_facts(declared: list[str], found: list[str]) -> list[str]:
    """
    Join the editor's declared facts and the found ones without repeating a
    fact that has the same canonical form.

    Input:
        . declared      : facts the editor listed
        . found         : facts extract_facts found
    Output:
        . facts         : declared first, then new found facts
    """
    seen: set[str] = set()
    facts: list[str] = []
    for fact in [*declared, *found]:
        key = canonical(fact)
        if key not in seen:
            seen.add(key)
            facts.append(fact)
    return facts
