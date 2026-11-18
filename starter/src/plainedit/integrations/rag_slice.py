"""The Langflow slice in code: "ask the guidelines" = retriever | prompt | model.

Every setting comes from config.flow, so this chain and the Langflow flow
(flows/FLOW_SPEC.json is written from the same values) cannot drift apart.
"""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    functools                       import  partial
from    typing                          import  Any

from    langchain_core.documents                    import  Document
from    langchain_core.language_models.chat_models  import  BaseChatModel
from    langchain_core.output_parsers               import  StrOutputParser
from    langchain_core.prompts                      import  ChatPromptTemplate
from    langchain_core.runnables                    import  Runnable, RunnableLambda, RunnablePassthrough

from    plainedit.config                  import  Config
from    plainedit.knowledge.vector_store  import  VectorStore


#==========================================================================
# Chunks to one context text
#==========================================================================
def format_context(documents: list[Document], *, pattern: str) -> str:
    """
    Write each retrieved chunk with the Parser pattern of the flow, e.g.
    "[{chunk_id}] {text}", one per line.

    Input:
        . documents     : retrieved chunks with their metadata
        . pattern       : flow.parser_pattern; {text} and metadata keys
    Output:
        . context       : the numbered context for the prompt
    """
    return "\n".join(pattern.format(text=item.page_content, **item.metadata) for item in documents)


#==========================================================================
# The chain
#==========================================================================
def build_rag_chain(config: Config, *, store: VectorStore, chat: BaseChatModel) -> Runnable:
    """
    Build {context: retriever | parser, question} | prompt | chat | text.

    Input:
        . config        : flow settings (k, system, template, parser_pattern)
        . store         : the guideline collection
        . chat          : any LangChain chat model
    Output:
        . chain         : invoke("a question") -> the answer text
    """
    flow    = config.flow
    parse   = RunnableLambda(partial(format_context, pattern=flow.parser_pattern))
    prompt  = ChatPromptTemplate.from_messages([("system", flow.system), ("human", flow.template)])
    return (
        {"context": store.retriever(k=flow.k) | parse, "question": RunnablePassthrough()}
        | prompt
        | chat
        | StrOutputParser()
    )


#==========================================================================
# Answer and sources
#==========================================================================
def ask_guidelines(config: Config, *, store: VectorStore, chat: BaseChatModel, question: str) -> dict[str, Any]:
    """
    Answer one guideline question and report which rules were retrieved.

    Input:
        . config        : flow settings
        . store         : the guideline collection
        . chat          : any LangChain chat model
        . question      : e.g. "When should I write must instead of shall?"
    Output:
        . answer        : {"question", "answer", "rule_ids"}
    """
    documents = store.retriever(k=config.flow.k).invoke(question)
    text      = build_rag_chain(config, store=store, chat=chat).invoke(question)
    return {"question": question, "answer": text, "rule_ids": [item.metadata["rule_id"] for item in documents]}
