"""The project's rules for the fake model: --fake runs and the fast tests.

The fake never reads meaning. It makes the loop visible and testable:
  . critique: one grounded finding (the first words of the notice, rule 1) and one
    UNgrounded finding that the code must drop
  . rewrite: mechanical changes (shall -> must, long sentences cut at
    ", and" / ", which" / ";"); the FIRST attempt drops the last sentence
    that holds a number, an attempt that follows code feedback keeps it
Fake results are for checking code only; saved results record the backend.
"""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  re
from    typing                          import  Any

from    plainedit.checks.metrics        import  split_sentences
from    plainedit.config                import  EditorConfig
from    plainedit.llm.fake_chat_model   import  FakeRules


#==========================================================================
# Rules used by --fake and by the fake model server
#==========================================================================
def project_fake_rules() -> FakeRules:
    """
    Return the rules the fake backend answers with.

    Output:
        . rules         : FakeRules with structured (Critique) and text (rewrite, answers)
    """
    return FakeRules(structured=_structured, text=_text)


#==========================================================================
# The notice inside a prompt
#==========================================================================
def _notice(prompt: str) -> str:
    """
    Cut the text between the last <notice> and </notice> lines of a prompt.

    Input:
        . prompt        : every message's text joined by newlines
    Output:
        . notice        : the notice, or "" when the prompt has none
    """
    found = re.findall(r"<notice>\n(.*?)\n</notice>", prompt, re.DOTALL)
    return found[-1] if found else ""


#==========================================================================
# Structured answers
#==========================================================================
def _structured(schema_name: str, prompt: str) -> dict[str, Any]:
    """
    Answer the Critique schema: one finding that is grounded in the notice
    and one that is not (so the grounding filter has something to drop).

    Input:
        . schema_name   : the Pydantic class name
        . prompt        : the whole prompt
    Output:
        . fields        : {"findings": [...]}
    """
    if schema_name != "Critique":
        raise ValueError(f"fake model has no rule for schema {schema_name!r}")
    issues = re.search(r"already detected: (.*)", prompt)
    issue  = (issues.group(1).split(",")[0].strip() if issues else "") or "passive"
    quote  = " ".join(re.sub(r"^\d+\.\s*", "", _notice(prompt)).split()[:5])
    return {
        "findings": [
            {"issue": issue, "quote": quote, "rule": 1},
            {"issue": issue, "quote": "[FAKE] this quote is not in the notice", "rule": 1},
        ]
    }


#==========================================================================
# Text answers
#==========================================================================
def _text(prompt: str) -> str:
    """
    Write a mechanical rewrite when the prompt holds a notice, else a
    placeholder answer.

    Input:
        . prompt        : every message's text, the last one last
    Output:
        . text          : the fake answer
    """
    notice = _notice(prompt)
    if not notice:
        return "[FAKE MODEL ANSWER] " + " ".join(prompt.split()[-24:])
    sentences = split_sentences(notice, editor=EditorConfig())
    numbered  = [item for item in sentences if re.search(r"[\d$]", item)]
    if "Your last attempt failed" not in prompt and len(numbered) >= 2:
        sentences = [item for item in sentences if item != numbered[-1]]
    out = " ".join(_simplify(item) for item in sentences)
    return out


#==========================================================================
# One sentence
#==========================================================================
def _simplify(sentence: str) -> str:
    """
    Cut a sentence at its joints and replace shall by must.

    Input:
        . sentence      : one sentence of the notice
    Output:
        . text          : the same words, shorter sentences
    """
    sentence = re.sub(r"\bshall\b", "must", sentence)
    parts    = re.split(r",? (?:and|which|while|since) |; ", sentence)
    pieces   = [part.strip(" .") for part in parts]
    return " ".join(piece[0].upper() + piece[1:] + "." for piece in pieces if piece)
