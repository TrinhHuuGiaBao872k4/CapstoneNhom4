"""T08 (Langflow): compare_answers, the code slice, FLOW_SPEC, flow-compare against a fake Langflow."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
from    pathlib                         import  Path

import  pytest
from    fake_langflow                   import  FLOW_NAME, FakeLangflow

from    helpers                              import  ROOT, plain_deps, project_copy
from    main                                 import  main
from    plainedit.config                     import  load_config
from    plainedit.integrations.flow_compare  import  compare_answers
from    plainedit.integrations.rag_slice     import  ask_guidelines, format_context
from    plainedit.runtime.flow_commands      import  flow_spec_values


#==========================================================================
# T08: compare_answers
#==========================================================================
def test_t08_compare_answers_verdicts() -> None:
    """
    Pin T08: an answer is OK when it holds any expect_any word (any case);
    the verdict is both, code_only, flow_only or neither.
    """
    questions = [{"id": f"Q{n}", "expect_any": ["must", "obligation"]} for n in range(1, 5)]
    code = ["Use MUST for a requirement.", "Use must.", "I do not know.", "An obligation."]
    flow = ["It is an obligation.", "No idea.", "must", "Nothing."]
    rows = compare_answers(questions, code, flow)
    assert [row["verdict"] for row in rows] == ["both", "code_only", "flow_only", "code_only"]
    assert rows[0] == {"id": "Q1", "code_ok": True, "flow_ok": True, "verdict": "both"}
    assert rows[3]["flow_ok"] is False


#==========================================================================
# T08 compare answers refuses lists of different length
#==========================================================================
def test_t08_compare_answers_refuses_lists_of_different_length() -> None:
    """
    Pin T08: three questions and two answers is an error, not a silent cut.
    """
    with pytest.raises(ValueError):
        compare_answers([{"id": "Q1", "expect_any": ["a"]}] * 3, ["a", "a"], ["a", "a"])


#==========================================================================
# The code slice and the spec (given)
#==========================================================================
def test_format_context_uses_the_parser_pattern_of_the_flow() -> None:
    """
    Pin format_context: the pattern's {text} and metadata keys are filled per chunk.
    """
    from    langchain_core.documents        import  Document

    docs = [Document(page_content="Use must.", metadata={"chunk_id": "a#001"}), Document(page_content="Be brief.", metadata={"chunk_id": "b#002"})]
    assert format_context(docs, pattern="[{chunk_id}] {text}") == "[a#001] Use must.\n[b#002] Be brief."


#==========================================================================
# The code slice answers and names the rules it retrieved
#==========================================================================
def test_the_code_slice_answers_and_names_the_rules_it_retrieved(tmp_path: Path) -> None:
    """
    Pin the code slice on the fake model: an answer text and rule ids from the retrieval.

    Input:
        . tmp_path      : temporary folder
    """
    deps = plain_deps(tmp_path)
    out  = ask_guidelines(deps.config, store=deps.store, chat=deps.chat.get(), question="When should I write must instead of shall?")
    assert out["answer"].startswith("[FAKE MODEL ANSWER]") and len(out["rule_ids"]) == deps.config.flow.k


#==========================================================================
# Flow spec json matches the config
#==========================================================================
def test_flow_spec_json_matches_the_config() -> None:
    """
    Pin flows/FLOW_SPEC.json: it equals what flow-spec writes from the config,
    so the flow and the code use the same collection, prompt and parser pattern.
    """
    config = load_config(ROOT / "configs" / "app.toml", root=ROOT)
    spec   = json.loads((ROOT / "flows" / "FLOW_SPEC.json").read_text(encoding="utf-8"))
    assert spec == flow_spec_values(config)
    assert spec["collection"] == "plain-guidelines" and "{context}" in spec["template"] and "{question}" in spec["template"]
    assert spec["parser_pattern"] == "[{chunk_id}] {text}" and spec["k"] == 3


#==========================================================================
# T08: flow-compare end to end against the fake Langflow
#==========================================================================
def test_t08_cli_flow_compare_against_a_fake_langflow(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Pin T08 through main.py: the 5 questions go to the code slice (fake
    model) and to the fake Langflow; the table and results/flow_compare.json come out.

    Input:
        . tmp_path      : temporary folder
        . capsys        : captured output
        . monkeypatch   : sets LANGFLOW_API_KEY for this test only
    """
    monkeypatch.setenv("LANGFLOW_API_KEY", "test-value")
    config   = project_copy(tmp_path)
    langflow = FakeLangflow()
    with config.open("a", encoding="utf-8") as file:
        file.write("\n")
    text = config.read_text(encoding="utf-8").replace('langflow_url = "http://127.0.0.1:7860"', f'langflow_url = "{langflow.url}"')
    text = text.replace('flow_name = "plainedit-rag"', f'flow_name = "{FLOW_NAME}"')
    config.write_text(text, encoding="utf-8")

    #----------------------------------------------------------------------
    # Run flow-compare
    #----------------------------------------------------------------------
    base = ["--config", str(config), "--fake"]
    assert main([*base, "index"]) == 0
    capsys.readouterr()
    code = main([*base, "flow-compare"])
    langflow.close()
    out = capsys.readouterr().out
    assert code == 0 and out.count("rule retrieved by code") == 5 and "[OK] saved" in out
    saved = json.loads((tmp_path / "results" / "flow_compare.json").read_text(encoding="utf-8"))
    assert saved["backend"] == "fake" and len(saved["rows"]) == 5 and len(saved["flow"]) == 5
    assert langflow.requests[-1]["input_value"] == "When is passive voice acceptable?"


#==========================================================================
# flow-spec refuses the fake backend
#==========================================================================
def test_flow_spec_refuses_the_fake_backend(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    Pin flow-spec: with --fake it stops with one line and writes nothing,
    because the fake collection name would send the flow to the wrong place.

    Input:
        . tmp_path      : temporary folder
        . capsys        : captured output
    """
    config = project_copy(tmp_path)
    assert main(["--config", str(config), "--fake", "flow-spec"]) == 2
    assert "without --fake" in capsys.readouterr().err
    assert main(["--config", str(config), "flow-spec"]) == 0
    assert json.loads((tmp_path / "flows" / "FLOW_SPEC.json").read_text(encoding="utf-8"))["collection"] == "plain-guidelines"
