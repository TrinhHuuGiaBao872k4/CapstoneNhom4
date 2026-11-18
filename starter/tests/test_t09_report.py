"""T09 (report): REPORT.md is filled with what you really saw."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    helpers                         import  ROOT


#==========================================================================
# T09
#==========================================================================
def test_t09_report_has_no_todo_left_and_names_real_numbers() -> None:
    """
    Pin T09: REPORT.md has no "<TODO" marker, and its tables hold numbers
    (a line with a score from results/ and a line that names a limit).
    """
    text = (ROOT / "REPORT.md").read_text(encoding="utf-8")
    if "<TODO" in text:
        raise NotImplementedError("T09: fill REPORT.md (every <TODO ...> marker)")
    assert "## 1." in text and "## 5." in text
    assert "facts_kept" in text and "heuristic" in text.lower()
