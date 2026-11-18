"""Turn the raw snapshot into the prepared files, deterministically.

Usage: python scripts/prepare_data.py

Reads   data/raw/_pages/guidelines/**/*.md   (U.S. Federal Plain Language Guidelines)
        data/drafts.json                     (authored for this course: 12 dev notices)
        holdout/holdout_drafts.json          (authored, instructor only; skipped when absent)
Writes  data/guidelines.json                 one record per guideline page, with attribution
        data/docs/guidelines_kb.json         the same pages in the shape `index` reads
        data/word_swaps.json                 complex word -> simple word
        data/dev_cases.json, holdout/holdout_cases.json
"""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
import  re
import  tomllib
from    dataclasses                     import  dataclass
from    pathlib                         import  Path
from    typing                          import  Any

import  yaml


#==========================================================================
# Settings of the preparation
#==========================================================================
@dataclass(frozen=True)
class PrepareConfig:
    """
    Purpose: where the files are, which pages count as content, and which
    entries of the guideline word table become word_swaps.json.
    """

    root: Path                          = Path(__file__).resolve().parents[1]
    pages_dir: str                      = "data/raw/_pages/guidelines"
    swaps_page: str                     = "words/use-simple-words-phrases.md"
    min_words: int                      = 60        # shorter pages are navigation only

    #----------------------------------------------------------------------
    # Entries of the guideline word table that the editor flags
    #----------------------------------------------------------------------
    swap_terms: tuple[str, ...]         = (
        "utilize", "utilization", "commence", "terminate", "prior to", "pursuant to", "in accordance with",
        "assist", "assistance", "in the event of", "in the amount of", "ascertain", "endeavor", "notify",
        "sufficient", "numerous", "additional", "demonstrate", "require", "reside", "purchase",
        "remuneration", "facilitate", "initiate", "in order to", "due to the fact that",
        "at the present time", "in lieu of", "with reference to", "pertaining to", "in regard to",
        "expiration", "modify", "attempt", "indicate", "subsequent", "expedite", "failed to",
        "has a requirement for", "in a timely manner", "for a period of", "comply with", "retain",
        "disclose", "ensure",
    )
    inflect_verbs: tuple[str, ...]      = (
        "utilize", "commence", "terminate", "ascertain", "endeavor", "notify", "demonstrate", "assist",
        "require", "reside", "purchase", "facilitate", "initiate", "modify", "attempt", "indicate",
        "expedite", "retain", "disclose", "ensure", "obtain",
    )

    #----------------------------------------------------------------------
    # Pairs that the guideline table does not list (authored, marked as such)
    #----------------------------------------------------------------------
    authored_swaps: tuple[tuple[str, str], ...] = (
        ("in the event that", "if"),
        ("subsequent to", "after"),
        ("approximately", "about"),
        ("obtain", "get"),
        ("a majority of", "most"),
    )


#==========================================================================
# Read one page
#==========================================================================
def read_page(path: Path, *, pages_root: Path) -> dict[str, Any]:
    """
    Split a Markdown page into front matter and body, and clean the body of
    Liquid, HTML, Markdown markup and table separators.

    Input:
        . path          : one guideline .md file
        . pages_root    : data/raw/_pages/guidelines
    Output:
        . page          : rule_id, section, title, text, sources (attribution lines)
    """
    raw = path.read_text(encoding="utf-8")
    _, front, body = raw.split("---", 2)
    meta     = yaml.safe_load(front)
    rule_id  = path.relative_to(pages_root).with_suffix("").as_posix()
    sources  = [
        f"{item.get('author', '')}, {' '.join(str(item.get('title', '')).split())} ({item.get('date', 'n.d.')})"
        for item in meta.get("sources", [])
    ]
    return {
        "rule_id": rule_id,
        "section": rule_id.split("/")[0],
        "title": " ".join(str(meta["title"]).split()),
        "text": clean_body(body),
        "sources": sources,
    }


#==========================================================================
# Clean a Markdown body
#==========================================================================
def clean_body(body: str) -> str:
    """
    Remove markup the embedding model should not see; keep the words and
    turn table rows into "left | right" lines.

    Input:
        . body          : Markdown after the front matter
    Output:
        . text          : plain text, one paragraph per line
    """
    lines = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("{:") or line.startswith("{%") or re.fullmatch(r"[-| :]+", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"^[*-]\s+####\s*", "", line)
        line = re.sub(r"^#+\s*", "", line)
        line = line.replace("**", "").replace("\\_", "_").replace("{{", "").replace("}}", "")
        if line:
            lines.append(line)
    return "\n".join(lines)


#==========================================================================
# Word table to swap pairs
#==========================================================================
def build_swaps(page_text: str, config: PrepareConfig) -> list[dict[str, str]]:
    """
    Read the "Don't say | Say" table of the simple-words page, keep the
    configured terms, add inflected verb forms, and the authored extras.

    Input:
        . page_text     : the raw Markdown of words/use-simple-words-phrases.md
        . config        : swap_terms, inflect_verbs, authored_swaps
    Output:
        . swaps         : [{complex, simple, source}] sorted by complex
    """

    #----------------------------------------------------------------------
    # Read the table rows: left side may list several words
    #----------------------------------------------------------------------
    table: dict[str, str] = {}
    for line in page_text.splitlines():
        if "|" not in line or line.startswith("---") or "Don" in line:
            continue
        left, right = (part.replace("**", "").strip() for part in line.split("|", 1))
        options     = [item.strip() for item in right.split(",") if item.strip() and not item.strip().startswith("(")]
        if not options:
            continue
        for term in (item.strip() for item in left.split(",")):
            table.setdefault(term.lower(), options[0])
    missing = [term for term in config.swap_terms if term not in table]
    if missing:
        raise ValueError(f"swap_terms not in the guideline table: {missing}")

    #----------------------------------------------------------------------
    # Pick the terms, add inflections, add the authored pairs
    #----------------------------------------------------------------------
    pairs   = {term: (table[term], "guideline table") for term in config.swap_terms}
    for complex_word, simple in config.authored_swaps:
        pairs.setdefault(complex_word, (simple, "authored"))
    for verb in config.inflect_verbs:
        simple, source = pairs[verb]
        for form in inflect(verb):
            pairs.setdefault(form, (simple, source))
    return [{"complex": key, "simple": pairs[key][0], "source": pairs[key][1]} for key in sorted(pairs)]


#==========================================================================
# Inflected forms of a verb
#==========================================================================
def inflect(verb: str) -> list[str]:
    """
    Write the -s, -ed and -ing forms of a regular verb.

    Input:
        . verb          : base form, e.g. "terminate", "modify", "assist"
    Output:
        . forms         : three inflected forms
    """
    if verb.endswith("e"):
        return [verb + "s", verb + "d", verb[:-1] + "ing"]
    if verb.endswith("y") and verb[-2] not in "aeiou":
        return [verb[:-1] + "ies", verb[:-1] + "ied", verb + "ing"]
    return [verb + "s", verb + "ed", verb + "ing"]


#==========================================================================
# Cases from drafts
#==========================================================================
def build_cases(drafts: list[dict[str, Any]], *, sentence_limit: int, split: str) -> list[dict[str, Any]]:
    """
    Turn authored drafts into evaluation cases. Expected values come from the
    drafts' own lists (hand-written from the text), never from a model.

    Input:
        . drafts        : draft_id, kind, note, text, planted, facts, required_terms, forbidden_terms
        . sentence_limit: the words-per-sentence limit of configs/app.toml
        . split         : "dev" or "holdout"
    Output:
        . cases         : {id, inputs, outputs, kind, note, split}
    """

    #----------------------------------------------------------------------
    # Build one case per draft
    #----------------------------------------------------------------------
    return [
        {
            "id": draft["draft_id"],
            "inputs": {"draft_id": draft["draft_id"], "text": draft["text"], "facts": draft["facts"]},
            "outputs": {
                "facts": draft["facts"],
                "planted": draft["planted"],
                "sentence_limit": sentence_limit,
                "required_terms": draft.get("required_terms", []),
                "forbidden_terms": draft.get("forbidden_terms", []),
            },
            "kind": draft["kind"],
            "note": draft["note"],
            "split": split,
        }
        for draft in drafts
    ]


#==========================================================================
# Write a JSON file
#==========================================================================
def write_json(path: Path, value: Any) -> None:
    """
    Write JSON with a stable layout (sorted by the caller, 1-space indent).

    Input:
        . path          : target file; its folder is created
        . value         : JSON-serialisable data
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


#==========================================================================
# Entry point
#==========================================================================
def main() -> int:
    """
    Prepare every data file and print one line per file.

    Output:
        . code          : 0
    """

    #----------------------------------------------------------------------
    # Guideline pages: drop navigation pages, write both shapes
    #----------------------------------------------------------------------
    config     = PrepareConfig()
    pages_root = config.root / config.pages_dir
    pages      = [read_page(path, pages_root=pages_root) for path in sorted(pages_root.rglob("*.md"))]
    pages      = [page for page in pages if len(page["text"].split()) >= config.min_words]
    write_json(config.root / "data" / "guidelines.json", pages)
    kb = [
        {
            "source_id": page["rule_id"],
            "title": page["title"],
            "text": f"{page['title']}. {page['text']}",
            "rule_id": page["rule_id"],
            "section": page["section"],
        }
        for page in pages
    ]
    write_json(config.root / "data" / "docs" / "guidelines_kb.json", kb)
    print(f"[OK] guidelines: {len(pages)} pages, {sum(len(page['text'].split()) for page in pages)} words")

    #----------------------------------------------------------------------
    # Word swaps from the guideline table
    #----------------------------------------------------------------------
    swaps = build_swaps((pages_root / config.swaps_page).read_text(encoding="utf-8"), config)
    write_json(config.root / "data" / "word_swaps.json", swaps)
    print(f"[OK] word_swaps: {len(swaps)} pairs")

    #----------------------------------------------------------------------
    # Cases from the authored drafts
    #----------------------------------------------------------------------
    with (config.root / "configs" / "app.toml").open("rb") as file:
        limit = tomllib.load(file)["editor"]["sentence_limit"]
    dev = json.loads((config.root / "data" / "drafts.json").read_text(encoding="utf-8"))
    write_json(config.root / "data" / "dev_cases.json", build_cases(dev, sentence_limit=limit, split="dev"))
    print(f"[OK] dev_cases: {len(dev)} cases")
    holdout_file = config.root / "holdout" / "holdout_drafts.json"
    if holdout_file.exists():
        drafts = json.loads(holdout_file.read_text(encoding="utf-8"))
        write_json(config.root / "holdout" / "holdout_cases.json", build_cases(drafts, sentence_limit=limit, split="holdout"))
        print(f"[OK] holdout_cases: {len(drafts)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
