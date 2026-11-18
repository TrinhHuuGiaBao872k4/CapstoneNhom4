"""Read the prepared data files: word swaps, drafts, guideline rules."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
from    pathlib                         import  Path
from    typing                          import  Any

from    plainedit.config                import  Config


#==========================================================================
# Word swaps
#==========================================================================
def load_swaps(config: Config) -> list[dict[str, str]]:
    """
    Read data/word_swaps.json: the complex words and phrases the editor flags.

    Input:
        . config        : paths.data_dir
    Output:
        . swaps         : rows with complex, simple, source
    """
    return json.loads((config.paths.data_dir / "word_swaps.json").read_text(encoding="utf-8"))


#==========================================================================
# Drafts
#==========================================================================
def load_drafts(config: Config) -> list[dict[str, Any]]:
    """
    Read data/drafts.json: the authored Riverton notices that learners may use.

    Input:
        . config        : paths.data_dir
    Output:
        . drafts        : rows with draft_id, text, facts, planted, kind
    """
    return json.loads((config.paths.data_dir / "drafts.json").read_text(encoding="utf-8"))


#==========================================================================
# Find a draft by id
#==========================================================================
def find_draft(config: Config, draft_id: str) -> dict[str, Any] | None:
    """
    Look a draft up by its id (case-insensitive); None when there is none.

    Input:
        . config        : paths.data_dir
        . draft_id      : e.g. "D07"
    Output:
        . draft         : the row, or None
    """
    for draft in load_drafts(config):
        if draft["draft_id"].lower() == draft_id.lower():
            return draft
    return None


#==========================================================================
# Questions for the Langflow slice
#==========================================================================
def load_questions(config: Config) -> list[dict[str, Any]]:
    """
    Read the guideline questions used by flow-compare.

    Input:
        . config        : paths.root and flow.questions_file
    Output:
        . questions     : rows with id, question, expect_rule, expect_any
    """
    return json.loads((Path(config.paths.root) / config.flow.questions_file).read_text(encoding="utf-8"))
