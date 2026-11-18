"""The project's config sections and the fake model rules."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  re

import  pytest

from    helpers                         import  ROOT
from    plainedit.config                import  EditorConfig, RetrievalConfig, load_config
from    plainedit.llm.fake_chat_model   import  FakeChatModel
from    plainedit.llm.fake_rules        import  project_fake_rules


#==========================================================================
# Config
#==========================================================================
def test_app_toml_loads_and_every_key_is_known() -> None:
    """
    Pin configs/app.toml: it loads into the frozen classes, the values are
    the ones the design asks for, and every regular expression compiles.
    """
    config = load_config(ROOT / "configs" / "app.toml", root=ROOT)
    editor = config.editor
    assert editor.max_rounds == 3 and editor.sentence_limit == 25 and editor.max_findings == 4
    assert config.knowledge.collection == "plain-guidelines" and config.model.chat_model == "Qwen/Qwen2.5-1.5B-Instruct"
    for pattern in (*editor.hidden_verb_patterns, *editor.double_negative_patterns, *editor.injection_patterns):
        re.compile(pattern)
    assert config.paths.holdout_dir == ROOT / "holdout"


#==========================================================================
# The defaults in code equal the values in the toml file
#==========================================================================
def test_the_defaults_in_code_equal_the_values_in_the_toml_file() -> None:
    """
    Pin that app.toml and the dataclass defaults say the same (no silent drift).
    """
    config = load_config(ROOT / "configs" / "app.toml", root=ROOT)
    assert config.editor == EditorConfig() and config.retrieval == RetrievalConfig()


#==========================================================================
# Every issue type has a search section and query
#==========================================================================
def test_every_issue_type_has_a_search_section_and_query() -> None:
    """
    Pin RetrievalConfig.for_issue for each issue type the editor detects.
    """
    retrieval = RetrievalConfig()
    for issue in EditorConfig().issue_types:
        section, query = retrieval.for_issue(issue)
        assert section and query


#==========================================================================
# Fake rules
#==========================================================================
def test_the_fake_model_writes_a_visible_fake_rewrite_and_an_ungrounded_finding() -> None:
    """
    Pin the fake rules: a rewrite swaps shall for must and cuts sentences,
    the first attempt drops the last numbered sentence, a retry keeps it; a
    prompt without a notice gets a [FAKE MODEL ANSWER].
    """
    rules  = project_fake_rules()
    notice = "You shall pay $5 by 1 May 2027, and you shall sign. Room 12 is open on 2 May 2027."
    first  = rules.text(f"<notice>\n{notice}\n</notice>")
    retry  = rules.text(f"Your last attempt failed the code check.\n<notice>\n{notice}\n</notice>")
    assert "must" in retry and "Room 12" in retry and "Room 12" not in first
    assert rules.text("Context: x\nQuestion: y").startswith("[FAKE MODEL ANSWER]")
    findings = rules.structured("Critique", "Problems the code already detected: passive, shall\n<notice>\n1. Pay now please.\n</notice>")["findings"]
    assert findings[0]["quote"] == "Pay now please." and findings[1]["quote"].startswith("[FAKE]")
    with pytest.raises(ValueError, match="no rule for schema"):
        rules.structured("Other", "")


#==========================================================================
# The fake chat model is deterministic
#==========================================================================
def test_the_fake_chat_model_is_deterministic() -> None:
    """
    Pin that the same prompt gives the same text twice.
    """
    chat = FakeChatModel(rules=project_fake_rules())
    assert chat.invoke("hello").content == chat.invoke("hello").content
