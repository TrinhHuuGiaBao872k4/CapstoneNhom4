"""T07 (LangSmith): v1 and v2 as experiments on the fake backend, saved results and compare."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
from    pathlib                         import  Path

import  pytest

from    helpers                          import  ROOT, plain_deps, project_copy
from    main                             import  main
from    plainedit.evaluation.compare     import  compare_experiments
from    plainedit.evaluation.dataset     import  load_dataset
from    plainedit.evaluation.evaluators  import  default_evaluators
from    plainedit.evaluation.experiment  import  run_experiment
from    plainedit.evaluation.targets     import  EditTarget


#==========================================================================
# T07: an experiment on the fake backend
#==========================================================================
def test_t07_v2_keeps_facts_where_the_fake_v1_loses_them_and_compare_shows_it(tmp_path: Path) -> None:
    """
    Pin T06 end to end on the 12 dev cases with the fake model: the fake's
    first attempt drops a fact; v1 (one shot) keeps it dropped, v2 (loop) is
    told by the code and restores it. compare_experiments lists better cases.

    Input:
        . tmp_path      : temporary folder
    """
    deps    = plain_deps(tmp_path)
    dataset = load_dataset(ROOT / "data" / "dev_cases.json")
    first   = run_experiment("v1", EditTarget("v1", deps, trace_dir=None), dataset, default_evaluators(), backend="fake")
    second  = run_experiment("v2", EditTarget("v2", deps, trace_dir=tmp_path / "traces"), dataset, default_evaluators(), backend="fake")
    assert first.summary["errors"] == second.summary["errors"] == 0
    assert second.summary["scores"]["facts_kept"] > first.summary["scores"]["facts_kept"]
    assert second.summary["scores"]["findings_grounded"] == 1.0
    result = compare_experiments(first, second)
    assert result.better and "better:" in "\n".join(result.lines)
    assert sorted(path.name for path in (tmp_path / "traces").iterdir())[:2] == ["eval-v2-D01.json", "eval-v2-D02.json"]
    assert second.summary["model_calls"] > first.summary["model_calls"] == 12


#==========================================================================
# T06 cli eval saves results that compare reads
#==========================================================================
def test_t07_cli_eval_saves_results_that_compare_reads(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    Pin T06 through main.py: eval v1 and eval v2 save results/<name>.json
    with the backend "fake", and compare prints better and worse cases.

    Input:
        . tmp_path      : temporary folder
        . capsys        : captured output
    """
    config = project_copy(tmp_path)
    base   = ["--config", str(config), "--fake"]
    assert main([*base, "index"]) == 0
    assert main([*base, "eval", "v1"]) == 0
    assert main([*base, "eval", "v2"]) == 0
    saved = json.loads((tmp_path / "results" / "v2.json").read_text(encoding="utf-8"))
    assert saved["backend"] == "fake" and saved["summary"]["cases"] == 12
    capsys.readouterr()
    assert main([*base, "compare", "v1", "v2"]) == 0
    out = capsys.readouterr().out
    assert "v1 (fake) -> v2 (fake)" in out and "better:" in out and "worse:" in out
    assert main([*base, "eval", "v2", "--split", "holdout"]) in (0, 2)
