"""main.py project commands on the fake backend: ask, resume, submit-check."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
from    dataclasses                     import  replace
from    pathlib                         import  Path

import  pytest

from    helpers                         import  fake_config, project_copy
from    main                            import  main
from    plainedit.config                import  PathConfig
from    plainedit.runtime.submit_check  import  stops_left


#==========================================================================
# v1 needs no index and no graph
#==========================================================================
def test_ask_v1_prints_the_contract_of_one_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    Pin ask --version v1 on a draft id: one pass, no findings, rounds 1, the
    contract keys, and facts_missing computed by code (the fake drops a fact).

    Input:
        . tmp_path      : temporary folder
        . capsys        : captured output
    """
    config = project_copy(tmp_path)
    assert main(["--config", str(config), "--fake", "ask", "D07", "--version", "v1"]) == 0
    contract = json.loads(capsys.readouterr().out)
    assert list(contract) == ["draft_id", "original", "rewrite", "findings", "metrics_before", "metrics_after",
                              "facts_missing", "rounds", "status", "reason"]
    assert contract["findings"] == [] and contract["rounds"] == 1 and contract["facts_missing"]


#==========================================================================
# Ask free text needs the index and says so
#==========================================================================
def test_ask_free_text_needs_the_index_and_says_so(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    Pin the one-line error when the collection is empty (v2 needs retrieval).

    Input:
        . tmp_path      : temporary folder
        . capsys        : captured output
    """
    config = project_copy(tmp_path)
    assert main(["--config", str(config), "--fake", "ask", "You shall pay."]) == 2
    assert "python main.py index" in capsys.readouterr().err


#==========================================================================
# T05: ask in one call, resume in another
#==========================================================================
def test_t05_cli_ask_stops_at_the_editor_and_resume_finishes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    Pin the two-command path: ask prints status needs_editor and a thread id;
    resume --action edit finishes it from the checkpoint file; a second
    resume is refused; the published file has one line.

    Input:
        . tmp_path      : temporary folder
        . capsys        : captured output
    """
    config = project_copy(tmp_path)
    base   = ["--config", str(config), "--fake"]
    assert main([*base, "index"]) == 0
    capsys.readouterr()
    assert main([*base, "ask", "D02", "--thread", "demo"]) == 0
    captured = capsys.readouterr()
    pending  = json.loads(captured.out)
    assert pending["status"] == "needs_editor" and "[waiting] thread demo" in captured.err
    assert main([*base, "ask", "D02", "--thread", "demo"]) == 2
    capsys.readouterr()
    assert main([*base, "resume", "--thread", "demo", "--action", "edit", "--text", pending["rewrite"] + " Thank you."]) == 0
    final = json.loads(capsys.readouterr().out)
    assert final["status"] == "approved" and final["rewrite"].endswith("Thank you.")
    assert len((tmp_path / "runtime" / "published.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    assert main([*base, "resume", "--thread", "demo", "--action", "approve"]) == 2


#==========================================================================
# T05 cli resume edit needs a text
#==========================================================================
def test_t05_cli_resume_edit_needs_a_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    Pin that resume --action edit without --text is one clear line.

    Input:
        . tmp_path      : temporary folder
        . capsys        : captured output
    """
    config = project_copy(tmp_path)
    base   = ["--config", str(config), "--fake"]
    main([*base, "index"])
    main([*base, "ask", "D02", "--thread", "e"])
    capsys.readouterr()
    assert main([*base, "resume", "--thread", "e", "--action", "edit"]) == 2
    assert "--action edit needs --text" in capsys.readouterr().err


#==========================================================================
# submit-check
#==========================================================================
def test_stops_left_reads_the_markers_in_the_source(tmp_path: Path) -> None:
    """
    Pin stops_left: it lists every T0N that still raises NotImplementedError.

    Input:
        . tmp_path      : temporary folder
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text('raise NotImplementedError("T03: reducers")\nraise NotImplementedError("T01: x")\n', encoding="utf-8")
    config = replace(fake_config(tmp_path), paths=PathConfig(root=tmp_path))
    assert stops_left(config) == ["T01", "T03"]


#==========================================================================
# Submit check says no for fake results a missing flow and an ...
#==========================================================================
def test_t07_submit_check_says_no_for_fake_results_a_missing_flow_and_an_unfilled_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    Pin submit-check: [NO] for results from the fake backend, no exported
    flow, a REPORT.md with <TODO markers; [OK] for a clean key scan.

    Input:
        . tmp_path      : temporary folder
        . capsys        : captured output
    """

    #----------------------------------------------------------------------
    # A project with fake results, no exported flow, an unfilled report
    #----------------------------------------------------------------------
    config = project_copy(tmp_path)
    for flow in (tmp_path / "flows").glob("*.json"):
        if flow.name != "FLOW_SPEC.json":
            flow.unlink()                       # the copy keeps flows/: drop an exported flow, this case has none
    (tmp_path / "REPORT.md").write_text("# Report\n<TODO fill this>\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    base = ["--config", str(config), "--fake"]
    main([*base, "index"])
    main([*base, "eval", "v1"])
    main([*base, "eval", "v2"])
    capsys.readouterr()
    #----------------------------------------------------------------------
    # submit-check says [NO] for each of them
    #----------------------------------------------------------------------
    assert main(["--config", str(config), "submit-check"]) == 1
    out = capsys.readouterr().out
    assert "[NO] results/v1.json from backend fake (fake results do not count)" in out
    assert "[NO] no exported flow" in out and "[NO] REPORT.md still has <TODO" in out
    assert "[OK] no API key in the files" in out and "[OK] code stops" in out
