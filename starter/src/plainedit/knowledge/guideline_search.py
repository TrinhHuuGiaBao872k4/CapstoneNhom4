"""Find the guideline rules that match the issue types of a notice."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    typing                          import  Any

from    plainedit.config                  import  RetrievalConfig
from    plainedit.knowledge.vector_store  import  VectorStore


#==========================================================================
# Rules for the detected issues
#==========================================================================
def find_rules(store: VectorStore, issues: list[str], *, retrieval: RetrievalConfig) -> list[dict[str, Any]]:
    """
    For each issue type, search its guideline section with its query text,
    keep the top per_issue_k chunks, and keep one chunk per rule_id (the first
    one found) across all issue types.

    Input:
        . store         : the guideline collection (chunks have rule_id, section metadata)
        . issues        : detected issue types, e.g. ["passive", "shall"]
        . retrieval     : per_issue_k and the section/query of each issue (for_issue)
    Output:
        . rules         : dicts rule_id, section, title, chunk_id, text, score, issue; no repeated rule_id
    """
    #----------------------------------------------------------------------
    # Search each issue's guideline section and deduplicate by rule_id
    #----------------------------------------------------------------------
    seen_rules: set[str]       = set()
    rules: list[dict[str, Any]] = []

    for issue in issues:
        section, query = retrieval.for_issue(issue)
        retriever = store.retriever(k=retrieval.per_issue_k, where={"section": section})
        docs = retriever.invoke(query)

        for doc in docs:
            meta = doc.metadata
            rule_id = meta.get("rule_id")
            if rule_id in seen_rules:
                continue
            seen_rules.add(rule_id)
            rules.append(
                {
                    "rule_id": rule_id,
                    "section": meta.get("section", section),
                    "title": meta.get("title", ""),
                    "chunk_id": meta.get("chunk_id", ""),
                    "text": doc.page_content,
                    "score": meta.get("score", 0.0),
                    "issue": issue,
                }
            )

    return rules
