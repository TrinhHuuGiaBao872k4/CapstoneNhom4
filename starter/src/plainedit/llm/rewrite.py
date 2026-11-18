"""The rewrite chains: v2 (guidelines, findings, code feedback) and the v1 baseline."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  re

from    langchain_core.language_models.chat_models  import  BaseChatModel
from    langchain_core.output_parsers               import  StrOutputParser
from    langchain_core.prompts                      import  ChatPromptTemplate
from    langchain_core.runnables                    import  Runnable

from    plainedit.llm.prompts           import  BASELINE_HUMAN, BASELINE_SYSTEM, REWRITE_HUMAN, REWRITE_SYSTEM


#==========================================================================
# The v2 rewrite chain
#==========================================================================
def build_rewrite_chain(chat: BaseChatModel) -> Runnable:
    """
    Build prompt | chat | text for the v2 rewrite.

    Input:
        . chat          : any LangChain chat model
    Output:
        . chain         : invoke({"guidelines", "findings", "facts", "feedback", "draft"}) -> str
    """
    prompt = ChatPromptTemplate.from_messages([("system", REWRITE_SYSTEM), ("human", REWRITE_HUMAN)])
    return prompt | chat | StrOutputParser()


#==========================================================================
# The v1 baseline chain
#==========================================================================
def build_baseline_chain(chat: BaseChatModel) -> Runnable:
    """
    Build the v1 chain: one generic prompt, no guidelines, no facts, no loop.

    Input:
        . chat          : any LangChain chat model
    Output:
        . chain         : invoke({"draft"}) -> str
    """
    prompt = ChatPromptTemplate.from_messages([("system", BASELINE_SYSTEM), ("human", BASELINE_HUMAN)])
    return prompt | chat | StrOutputParser()


#==========================================================================
# Tidy the model's text
#==========================================================================
def clean_rewrite(text: str) -> str:
    """
    Remove what small models add around a rewrite: a leading "Here is ..."
    line, <notice> tags, and wrapping quotes. The words are never changed.

    Input:
        . text          : the raw model output
    Output:
        . clean         : the rewrite only
    """
    text  = re.sub(r"</?notice>", "", text).strip()
    lines = text.splitlines()
    if lines and re.match(r"^(here is|here's|sure|certainly|rewritten)\b.*:\s*$", lines[0].strip(), re.IGNORECASE):
        text = "\n".join(lines[1:]).strip()
    return text.strip().strip('"').strip()
