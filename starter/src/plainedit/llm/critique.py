"""The critique: the model names problems, code keeps only the grounded ones."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any, Literal

from    langchain_core.language_models.chat_models  import  BaseChatModel
from    langchain_core.prompts                      import  ChatPromptTemplate  # noqa: F401 (your stop uses it)
from    langchain_core.runnables                    import  Runnable
from    pydantic                                    import  BaseModel

from    plainedit.llm.prompts           import  CRITIQUE_HUMAN, CRITIQUE_SYSTEM  # noqa: F401 (your stop uses it)


#==========================================================================
# Structured output of the critique
#==========================================================================
class Finding(BaseModel):
    """
    Purpose: one problem the model found: the issue type, the first words of
    the sentence, and the NUMBER of the guideline that covers it (a 1.5B model
    copies the issue name when asked for a rule id; code maps the number to the
    rule id).
    """

    issue: Literal["long_sentence", "passive", "shall", "complex_words", "hidden_verb", "double_negative"]
    quote: str
    rule: int


#==========================================================================
# The whole critique
#==========================================================================
class Critique(BaseModel):
    """
    Purpose: the whole critique: a short list of findings (the code keeps at
    most editor.max_findings of them, and only the grounded ones).
    """

    findings: list[Finding]


#==========================================================================
# Guideline context for a prompt
#==========================================================================
def format_guidelines(rules: list[dict[str, Any]], *, words: int = 45) -> str:
    """
    Write retrieved rules as one numbered line each: "N. title (for issue):
    first words of the text". The model answers with the number N.

    Input:
        . rules         : dicts with title, issue and text (from find_rules)
        . words         : words of each rule's text to keep
    Output:
        . text          : one rule per line, or "(none)"
    """
    # TODO T01 -- one numbered line per rule: "<n>. <title> (for <issue>): <first `words` words of the text>",
    #     joined with newlines; return "(none)" when the list is empty.
    # CHECK: pytest -k t01 -- test_t01_format_guidelines_numbers_cuts_and_labels.
    if not rules:
        return "(none)"
    lines = []
    for i, rule in enumerate(rules, start=1):
        title = rule.get("title", "")
        issue = rule.get("issue", "")
        text = rule.get("text", "")
        first_words = " ".join(text.split()[:words])
        lines.append(f"{i}. {title} (for {issue}): {first_words}")
    return "\n".join(lines)

#==========================================================================
# The critique chain
#==========================================================================
def build_critique_chain(chat: BaseChatModel) -> Runnable:
    """
    Build prompt | structured output: input {guidelines, issues, draft}, output a Critique.

    Input:
        . chat          : any LangChain chat model
    Output:
        . chain         : a Runnable; invoke({"guidelines", "issues", "draft"}) -> Critique
    """
    
    # TODO T01 -- a ChatPromptTemplate from CRITIQUE_SYSTEM (system) and CRITIQUE_HUMAN (human),
    #     piped into chat.with_structured_output(Critique); return the chain.
    # CHECK: pytest -k t01 -- test_t01_critique_chain_returns_a_critique_from_the_fake_model (fake model, no download).
    prompt = ChatPromptTemplate.from_messages([
            ("system", CRITIQUE_SYSTEM),
            ("human", CRITIQUE_HUMAN)
        ])
    return prompt | chat.with_structured_output(Critique)