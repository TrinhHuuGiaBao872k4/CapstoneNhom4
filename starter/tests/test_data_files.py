"""The prepared data: authored drafts, cases, guidelines, word swaps, questions."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  hashlib
import  json
import  subprocess
import  sys

import  pytest

from    helpers                         import  ROOT
from    plainedit.checks.facts          import  missing_facts
from    plainedit.checks.guard          import  strip_instructions
from    plainedit.checks.metrics        import  count_words, detected_issues, find_issues
from    plainedit.config                import  EditorConfig


EDITOR = EditorConfig()


#==========================================================================
# Read a JSON file of the project
#==========================================================================
def read(relative: str) -> list[dict]:
    """
    Read a JSON list under the project root.

    Input:
        . relative      : e.g. "data/drafts.json"
    Output:
        . rows          : the parsed list
    """
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


#==========================================================================
# The authored drafts
#==========================================================================
def test_dev_drafts_cover_every_kind_the_course_needs() -> None:
    """
    Pin the 12 dev drafts and the kinds the design asks for: each issue
    type, two dense, one already plain, one injection, one legal shall.
    """
    drafts = read("data/drafts.json")
    kinds  = [draft["kind"] for draft in drafts]
    assert len(drafts) == 12
    assert kinds.count("dense_facts") == 2
    for kind in ("long_sentence", "passive", "shall", "complex_words", "hidden_verb", "double_negative",
                 "already_plain", "injection", "legal_shall", "mixed"):
        assert kind in kinds, kind


#==========================================================================
# Every draft is well formed
#==========================================================================
@pytest.mark.parametrize("relative", ["data/drafts.json", "holdout/holdout_drafts.json"])
def test_every_draft_is_well_formed(relative: str) -> None:
    """
    Pin per draft: 60-140 words, each fact written verbatim in the text, and
    each planted issue type really detected by the code metrics.

    Input:
        . relative      : the drafts file (the hold-out one exists only in the solution)
    """
    if not (ROOT / relative).exists():
        pytest.skip(f"{relative} is not in this folder")
    for draft in read(relative):
        assert 60 <= count_words(draft["text"]) <= 140, draft["draft_id"]
        assert missing_facts(draft["facts"], draft["text"]) == [], draft["draft_id"]
        clean, _ = strip_instructions(draft["text"], editor=EDITOR)
        swaps    = read("data/word_swaps.json")
        found    = detected_issues(find_issues(clean, editor=EDITOR, swaps=swaps), editor=EDITOR)
        assert set(found) == set(draft["planted"]), draft["draft_id"]
        assert "Riverton" in draft["text"] or draft["facts"], draft["draft_id"]


#==========================================================================
# Dev cases are built from the drafts by code
#==========================================================================
def test_dev_cases_are_built_from_the_drafts_by_code() -> None:
    """
    Pin dev_cases.json: same ids as the drafts, the contract's case shape,
    and expected values equal to the drafts' own lists.
    """
    drafts = {draft["draft_id"]: draft for draft in read("data/drafts.json")}
    cases  = read("data/dev_cases.json")
    assert [case["id"] for case in cases] == list(drafts)
    for case in cases:
        assert set(case) == {"id", "inputs", "outputs", "kind", "note", "split"}
        draft = drafts[case["id"]]
        assert case["inputs"] == {"draft_id": case["id"], "text": draft["text"], "facts": draft["facts"]}
        assert case["outputs"]["facts"] == draft["facts"] and case["outputs"]["planted"] == draft["planted"]
        assert case["outputs"]["sentence_limit"] == EDITOR.sentence_limit


#==========================================================================
# The trap cases carry their traps
#==========================================================================
def test_the_trap_cases_carry_their_traps() -> None:
    """
    Pin the injection and legal-shall cases: forbidden and required terms.
    """
    cases = {case["id"]: case for case in read("data/dev_cases.json")}
    assert {"waive", "free"} <= set(cases["D10"]["outputs"]["forbidden_terms"])
    assert "$45" in cases["D10"]["outputs"]["required_terms"]
    assert cases["D11"]["outputs"]["required_terms"] == ["must"]
    assert cases["D09"]["outputs"]["planted"] == []


#==========================================================================
# Holdout cases are the same kinds and not the dev ids
#==========================================================================
def test_holdout_cases_are_the_same_kinds_and_not_the_dev_ids() -> None:
    """
    Pin the 8 hold-out cases (solution only): disjoint ids, kinds from the dev set.
    """
    if not (ROOT / "holdout" / "holdout_cases.json").exists():
        pytest.skip("no hold-out in this folder")
    holdout = read("holdout/holdout_cases.json")
    dev     = read("data/dev_cases.json")
    assert len(holdout) == 8
    assert not {case["id"] for case in holdout} & {case["id"] for case in dev}
    assert {case["kind"] for case in holdout} <= {case["kind"] for case in dev}
    assert {case["split"] for case in holdout} == {"holdout"}


#==========================================================================
# Guidelines, swaps, questions
#==========================================================================
def test_guidelines_keep_content_pages_and_their_attribution() -> None:
    """
    Pin guidelines.json: navigation pages are gone, each page has a rule_id
    that starts with its section, and cited sources are kept.
    """
    pages = read("data/guidelines.json")
    assert 40 <= len(pages) <= 50
    assert all(len(page["text"].split()) >= 60 for page in pages)
    assert all(page["rule_id"].startswith(page["section"]) or page["rule_id"] == page["section"] for page in pages)
    assert "conversational/use-active-voice" in {page["rule_id"] for page in pages}
    assert any(page["sources"] for page in pages)
    kb = read("data/docs/guidelines_kb.json")
    assert [row["source_id"] for row in kb] == [page["rule_id"] for page in pages]


#==========================================================================
# Word swaps come from the table or are marked authored
#==========================================================================
def test_word_swaps_come_from_the_table_or_are_marked_authored() -> None:
    """
    Pin word_swaps.json: every row has complex, simple, source; authored rows are marked.
    """
    swaps = read("data/word_swaps.json")
    assert 30 <= len(swaps) <= 150
    assert {row["source"] for row in swaps} == {"guideline table", "authored"}
    assert all(row["complex"] == row["complex"].lower() and row["simple"] for row in swaps)
    assert {"utilize", "in the event that", "prior to"} <= {row["complex"] for row in swaps}


#==========================================================================
# Guideline questions name an existing rule
#==========================================================================
def test_guideline_questions_name_an_existing_rule() -> None:
    """
    Pin that each flow-compare question expects a rule that exists in guidelines.json.
    """
    rules = {page["rule_id"] for page in read("data/guidelines.json")}
    questions = read("data/guideline_questions.json")
    assert len(questions) == 5
    assert all(item["expect_rule"] in rules and item["expect_any"] for item in questions)


#==========================================================================
# Sources file says the drafts are authored
#==========================================================================
def test_sources_file_says_the_drafts_are_authored() -> None:
    """
    Pin data/SOURCES.md: the pinned SHA, the licence, and the authored-data label.
    """
    text = (ROOT / "data" / "SOURCES.md").read_text(encoding="utf-8")
    assert "fd7694740f19c0ed20ed71c2dd1dc92699e920fa" in text
    assert "CC0" in text and "public domain" in text
    assert "authored for this course" in text.lower() and "fictional" in text


#==========================================================================
# prepare_data.py is deterministic
#==========================================================================
def test_prepare_data_reproduces_the_committed_files() -> None:
    """
    Pin that scripts/prepare_data.py gives byte-identical files when run on
    the committed raw snapshot.
    """
    names  = ["data/guidelines.json", "data/docs/guidelines_kb.json", "data/word_swaps.json", "data/dev_cases.json"]
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
    result = subprocess.run([sys.executable, "scripts/prepare_data.py"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    after  = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
    assert before == after
