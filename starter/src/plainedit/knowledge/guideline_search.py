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
    # TODO T02 -- for each issue: (section, query) = retrieval.for_issue(issue); search with store.retriever(k=per_issue_k,
    #     where={"section": section}); keep one chunk per rule_id across ALL issues (first found wins);
    #     return dicts rule_id, section, title, chunk_id, text, score, issue.
    # CHECK: pytest -k t02 -- the three test_t02_* tests (hashing vectors, no download).
    raise NotImplementedError("T02: find_rules")
