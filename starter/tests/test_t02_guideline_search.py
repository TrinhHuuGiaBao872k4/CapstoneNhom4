"""T02 (LangChain / vector DB): retrieve the rules per issue type, one chunk per rule_id."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    pathlib                         import  Path

from    helpers                               import  hash_store
from    plainedit.config                      import  RetrievalConfig
from    plainedit.knowledge.chunking          import  Chunk
from    plainedit.knowledge.guideline_search  import  find_rules
from    plainedit.knowledge.vector_store      import  VectorStore


#==========================================================================
# A tiny guideline store
#==========================================================================
def tiny_store(tmp_path: Path) -> VectorStore:
    """
    Index five chunks of three rules in two sections with hashing vectors.

    Input:
        . tmp_path      : temporary folder
    Output:
        . store         : a store that returns every chunk (threshold below 0)
    """
    rows = [
        ("conversational/use-active-voice#001", "conversational/use-active-voice", "conversational", "Use active voice", "active voice says who does what"),
        ("conversational/use-active-voice#002", "conversational/use-active-voice", "conversational", "Use active voice", "passive sentences hide who acts"),
        ("conversational/shall-and-must#001", "conversational/shall-and-must", "conversational", "Shall and must", "use must not shall for a requirement"),
        ("words/avoid-hidden-verbs#001", "words/avoid-hidden-verbs", "words", "Avoid hidden verbs", "hidden verbs are verbs turned into nouns"),
        ("words/use-simple-words-phrases#001", "words/use-simple-words-phrases", "words", "Use simple words", "pick the familiar word"),
    ]
    store = hash_store(tmp_path, collection="tiny-rules", threshold=-1.0)
    store.index([
        Chunk(chunk_id, rule_id, title, text, {"rule_id": rule_id, "section": section})
        for chunk_id, rule_id, section, title, text in rows
    ])
    return store


#==========================================================================
# T02
#==========================================================================
def test_t02_each_issue_searches_its_own_section(tmp_path: Path) -> None:
    """
    Pin T02: rules for "passive" come from section conversational, rules
    for "hidden_verb" from section words, and each rule carries its issue.

    Input:
        . tmp_path      : temporary folder
    """
    rules = find_rules(tiny_store(tmp_path), ["passive", "hidden_verb"], retrieval=RetrievalConfig(per_issue_k=5))
    by_issue = {issue: {rule["section"] for rule in rules if rule["issue"] == issue} for issue in ("passive", "hidden_verb")}
    assert by_issue == {"passive": {"conversational"}, "hidden_verb": {"words"}}


#==========================================================================
# T02 a rule id appears once even with several chunks and issues
#==========================================================================
def test_t02_a_rule_id_appears_once_even_with_several_chunks_and_issues(tmp_path: Path) -> None:
    """
    Pin T02: two chunks of one rule give one entry; a rule found for one
    issue is not repeated for the next issue that searches the same section.

    Input:
        . tmp_path      : temporary folder
    """
    rules = find_rules(tiny_store(tmp_path), ["passive", "shall"], retrieval=RetrievalConfig(per_issue_k=5))
    ids   = [rule["rule_id"] for rule in rules]
    assert sorted(ids) == ["conversational/shall-and-must", "conversational/use-active-voice"]
    assert {rule["issue"] for rule in rules} == {"passive"}
    assert {"rule_id", "section", "title", "chunk_id", "text", "score", "issue"} <= set(rules[0])


#==========================================================================
# T02 top k limits chunks per issue and no issue gives nothing
#==========================================================================
def test_t02_top_k_limits_chunks_per_issue_and_no_issue_gives_nothing(tmp_path: Path) -> None:
    """
    Pin T02: per_issue_k = 1 gives at most one rule per issue; an empty
    issue list gives an empty list (and no search).

    Input:
        . tmp_path      : temporary folder
    """
    store = tiny_store(tmp_path)
    rules = find_rules(store, ["passive", "hidden_verb"], retrieval=RetrievalConfig(per_issue_k=1))
    assert [rule["issue"] for rule in rules] == ["passive", "hidden_verb"]
    assert find_rules(store, [], retrieval=RetrievalConfig()) == []
