# Sources of the data

## 1. The guidelines (real, fetched from GitHub)

- Repository: https://github.com/GSA/plainlanguage.gov (the U.S. Federal Plain Language Guidelines)
- Pinned commit SHA: `fd7694740f19c0ed20ed71c2dd1dc92699e920fa` (head of `main` on 2026-11-16)
- The repository is **archived** (read-only) on GitHub: the snapshot will not change.
- Files: 50 Markdown pages under `_pages/guidelines/` plus `LICENSE.md`, `README.md`, `CONTRIBUTING.md`
  (53 files, 177,105 bytes) in `data/raw/`; paths and sizes in `data/raw_manifest.json`.
  Re-download: `python scripts/fetch_data.py` (stdlib only, pinned SHA).
- Prepared by `python scripts/prepare_data.py` (deterministic):
  - `data/guidelines.json`: one record per page (rule_id = page path, section, title, cleaned text, `sources`
    = the page's own citations, kept as attribution). Navigation pages with fewer than 60 words are dropped
    (2 pages: `conversational/index`, `organize/index`), leaving 48 pages, about 22,000 words.
  - `data/docs/guidelines_kb.json`: the same pages in the shape `python main.py index` reads (collection `plain-guidelines`,
    chunks of 80 words with 20 overlap; metadata rule_id, section, title).
  - `data/word_swaps.json`: 113 pairs. Selected terms of the "Don't say / Say" table of
    `words/use-simple-words-phrases.md` (+ regular inflections of the verbs); 5 extra pairs are
    **authored** (`"source": "authored"`: in the event that, subsequent to, approximately, obtain, a majority of).

### Licence

- `LICENSE.md` of the repository: "As a work of the United States Government, this project is in the public domain
  within the United States."
- `CONTRIBUTING.md`: copyright and related rights are waived worldwide through the **CC0 1.0 Universal** public domain
  dedication (https://creativecommons.org/publicdomain/zero/1.0/).
- Caveat: some pages cite third-party books (Garner, Charrow and others) in their `sources` front matter. The public-domain
  statement covers the project's own text; reproduce the cited works only as short quotations. We keep the citations
  as attribution and do not copy those books.

## 2. The Riverton notices (AUTHORED for this course, fictional)

`data/drafts.json` (12 notices, dev) and, in the instructor copy only, `holdout/holdout_drafts.json` (8 notices) were
**written by the course author** for this course. They are not real data. "Riverton", every street, office, room number,
date, amount and fee is fictional; there are no real people or organisations. Each notice plants known problems
(long sentences, passive voice, "shall", complex words, hidden verbs, double negatives) and lists its `facts`
(what a rewrite must keep). `planted` is the set of issue types that the code metrics actually detect in the notice
(checked by `tests/test_data_files.py`); `facts` are written by hand and checked to appear verbatim in the text.
`dev_cases.json` and `holdout/holdout_cases.json` are built from them by code (`prepare_data.py`); no expected value
comes from a model.
