"""T07 (LangSmith): tags and metadata on every run, traces of the loop, and your notes."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
import  tomllib
from    pathlib                         import  Path

from    helpers                               import  ROOT, dev_case, plain_deps
from    plainedit.config                      import  TracingConfig
from    plainedit.evaluation.targets          import  EditTarget
from    plainedit.observability.local_tracer  import  LocalTracer
from    plainedit.observability.trace_config  import  case_config
from    plainedit.observability.trace_view    import  load_trace, tree_lines


#==========================================================================
# T07: the run config
#==========================================================================
def test_t07_case_config_tags_and_metadata() -> None:
    """
    Pin T07: the version is a tag, metadata has version, case_id and backend,
    the root run is named edit-<case>, and the tracer is a callback.
    """
    tracer = LocalTracer()
    config = case_config(TracingConfig(tags=("plainedit",)), version="v2", case_id="D07", backend="local", tracer=tracer)
    assert config["tags"] == ["plainedit", "v2"]
    assert config["metadata"] == {"version": "v2", "case_id": "D07", "backend": "local"}
    assert config["run_name"] == "edit-D07" and config["callbacks"] == [tracer]


#==========================================================================
# T07 without a tracer there is no callback
#==========================================================================
def test_t07_without_a_tracer_there_is_no_callback() -> None:
    """
    Pin T07: tracer=None adds no callbacks key (LangSmith alone needs none).
    """
    assert "callbacks" not in case_config(TracingConfig(), version="v1", case_id="D01", backend="fake")


#==========================================================================
# T07: what a trace of the loop shows
#==========================================================================
def test_t07_a_saved_trace_shows_the_rounds_the_lost_fact_and_the_feedback(tmp_path: Path) -> None:
    """
    Pin T07 with the fake model: the v2 trace of D07 has tagged runs, one
    "write" and one "check" run per round, the round-1 check output lists the
    lost fact, and the round-2 write input holds the FACTS MISSING feedback.

    Input:
        . tmp_path      : temporary folder
    """
    deps   = plain_deps(tmp_path)
    target = EditTarget("v2", deps, trace_dir=tmp_path / "traces")
    case   = dev_case("D07")["inputs"]
    target(case)
    rows   = load_trace(tmp_path / "traces" / "eval-v2-D07.json")
    root   = next(row for row in rows if row["parent"] is None)
    assert root["name"] == "edit-D07" and "v2" in root["tags"] and root["metadata"]["case_id"] == "D07"
    checks = [row for row in rows if row["name"] == "check"]
    writes = [row for row in rows if row["name"] == "write"]
    assert len(checks) == len(writes) >= 2
    assert checks[0]["outputs"]["attempts"][0]["facts_missing"] != []
    assert "FACTS MISSING" in "\n".join(checks[0]["outputs"]["feedback"])
    assert "FACTS MISSING" in str(writes[1]["inputs"]["feedback"])
    assert any("write" in line for line in tree_lines(rows))


#==========================================================================
# T07: your notes
#==========================================================================
def test_t07_notes_say_where_a_fact_was_lost_and_what_restored_it() -> None:
    """
    Pin T07: my_work/notes.toml is filled (no TODO left): the case exists in
    the dev set, the fact was lost in round r and restored in a later round by
    a FACTS MISSING feedback line that names the fact. When the trace file is
    there, the notes must match it.
    """

    #----------------------------------------------------------------------
    # Not filled yet
    #----------------------------------------------------------------------
    text = (ROOT / "my_work" / "notes.toml").read_text(encoding="utf-8")
    if "TODO" in text:
        raise NotImplementedError("T07: fill my_work/notes.toml (every TODO)")

    #----------------------------------------------------------------------
    # The notes are consistent
    #----------------------------------------------------------------------
    notes = tomllib.loads(text)
    lost  = notes["lost_fact"]
    ids   = {draft["id"] for draft in json.loads((ROOT / "data" / "dev_cases.json").read_text(encoding="utf-8"))}
    assert lost["case"] in ids
    assert isinstance(lost["round_lost"], int) and lost["round_lost"] >= 1
    assert lost["round_restored"] > lost["round_lost"]
    assert lost["feedback_that_restored_it"].startswith("FACTS MISSING") and lost["fact_lost"] in lost["feedback_that_restored_it"]
    assert notes["runs"]["compare_command"].startswith("python main.py compare")

    #----------------------------------------------------------------------
    # They match the trace, when the file is there
    #----------------------------------------------------------------------
    trace = ROOT / lost["trace_file"]
    if trace.exists():
        checks = [row for row in load_trace(trace) if row["name"] == "check"]
        attempts = [row["outputs"]["attempts"][0] for row in checks]
        assert lost["fact_lost"] in attempts[lost["round_lost"] - 1]["facts_missing"]
        assert lost["fact_lost"] not in attempts[lost["round_restored"] - 1]["facts_missing"]
        assert lost["feedback_that_restored_it"] in checks[lost["round_lost"] - 1]["outputs"]["feedback"]
