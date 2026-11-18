"""Re-download the raw snapshot of the plain language guidelines from GitHub.

Usage: python scripts/fetch_data.py [--out data/raw]

Downloads are pinned to one commit SHA, so the snapshot never changes. The
files are data only: this script writes them and never reads their content.
"""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  argparse
import  urllib.request
from    dataclasses                     import  dataclass
from    pathlib                         import  Path


#==========================================================================
# What to download
#==========================================================================
@dataclass(frozen=True)
class FetchConfig:
    """
    Purpose: the repository, the pinned commit and the exact files of the
    snapshot (50 guideline pages plus the licence files).
    """

    repo: str                           = "GSA/plainlanguage.gov"
    sha: str                            = "fd7694740f19c0ed20ed71c2dd1dc92699e920fa"   # head of main on 2026-11-16
    timeout: float                      = 30.0
    files: tuple[str, ...]              = (
        "CONTRIBUTING.md",
        "LICENSE.md",
        "README.md",
        "_pages/guidelines/audience/address-separate-audiences-separately.md",
        "_pages/guidelines/audience/address-the-user.md",
        "_pages/guidelines/audience/do-your-research.md",
        "_pages/guidelines/audience/index.md",
        "_pages/guidelines/concise/index.md",
        "_pages/guidelines/concise/keep-the-subject-verb-and-object-close-together.md",
        "_pages/guidelines/concise/use-positive-language.md",
        "_pages/guidelines/concise/write-short-paragraphs.md",
        "_pages/guidelines/concise/write-short-sections.md",
        "_pages/guidelines/concise/write-short-sentences.md",
        "_pages/guidelines/conversational/dont-use-slashes.md",
        "_pages/guidelines/conversational/index.md",
        "_pages/guidelines/conversational/shall-and-must.md",
        "_pages/guidelines/conversational/use-active-voice.md",
        "_pages/guidelines/conversational/use-contractions.md",
        "_pages/guidelines/conversational/use-examples.md",
        "_pages/guidelines/conversational/use-must-to-indicate-requirements.md",
        "_pages/guidelines/conversational/use-the-present-tense.md",
        "_pages/guidelines/design/consider-using-visuals.md",
        "_pages/guidelines/design/highlight-important-concepts.md",
        "_pages/guidelines/design/index.md",
        "_pages/guidelines/design/minimize-cross-references.md",
        "_pages/guidelines/design/use-tables-to-make-complex-material-easier-to-understand.md",
        "_pages/guidelines/index.md",
        "_pages/guidelines/organize/add-useful-headings.md",
        "_pages/guidelines/organize/effective-headings.md",
        "_pages/guidelines/organize/have-a-topic-sentence.md",
        "_pages/guidelines/organize/index.md",
        "_pages/guidelines/organize/make-it-easy-to-follow.md",
        "_pages/guidelines/organize/place-the-main-idea-before-exceptions-and-conditions.md",
        "_pages/guidelines/organize/use-lists.md",
        "_pages/guidelines/organize/use-transition-words.md",
        "_pages/guidelines/test/controlled-comparative-studies.md",
        "_pages/guidelines/test/index.md",
        "_pages/guidelines/test/paraphrase-testing.md",
        "_pages/guidelines/test/usability-testing.md",
        "_pages/guidelines/web/avoid-faqs.md",
        "_pages/guidelines/web/avoid-pdf-overload.md",
        "_pages/guidelines/web/index.md",
        "_pages/guidelines/web/repurpose-print-material.md",
        "_pages/guidelines/web/write-effective-links.md",
        "_pages/guidelines/words/avoid-hidden-verbs.md",
        "_pages/guidelines/words/avoid-jargon.md",
        "_pages/guidelines/words/avoid-noun-strings.md",
        "_pages/guidelines/words/index.md",
        "_pages/guidelines/words/minimize-abbreviations.md",
        "_pages/guidelines/words/minimize-definitions.md",
        "_pages/guidelines/words/place-words-carefully.md",
        "_pages/guidelines/words/use-simple-words-phrases.md",
        "_pages/guidelines/words/use-the-same-terms-consistently.md",
    )

    #----------------------------------------------------------------------
    # Base URL of the pinned snapshot
    #----------------------------------------------------------------------
    @property
    def raw_base(self) -> str:
        """
        Build the raw.githubusercontent.com prefix for the pinned commit.

        Output:
            . url           : prefix ending with a slash
        """
        return f"https://raw.githubusercontent.com/{self.repo}/{self.sha}/"


#==========================================================================
# Download one file
#==========================================================================
def fetch_file(fetch: FetchConfig, relative: str) -> bytes:
    """
    Download one file of the snapshot.

    Input:
        . fetch         : repository, pinned commit, timeout
        . relative      : path inside the repository
    Output:
        . data          : the file's bytes
    """
    if relative.startswith("/") or ".." in relative.split("/"):
        raise ValueError(f"refusing an unsafe path: {relative}")
    request = urllib.request.Request(
        fetch.raw_base + relative, headers={"User-Agent": "course-data-fetch/1.0"}
    )
    with urllib.request.urlopen(request, timeout=fetch.timeout) as response:
        return response.read()


#==========================================================================
# Entry point
#==========================================================================
def main() -> int:
    """
    Download every file into --out, keeping the repository's relative paths.

    Output:
        . code          : 0 when every file was written
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "raw")
    args  = parser.parse_args()
    fetch = FetchConfig()
    total = 0
    for relative in fetch.files:
        data = fetch_file(fetch, relative)
        dest = args.out / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        total += len(data)
        print(f"{len(data):>8}  {relative}")
    print(f"done: {len(fetch.files)} files, {total} bytes, sha {fetch.sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
