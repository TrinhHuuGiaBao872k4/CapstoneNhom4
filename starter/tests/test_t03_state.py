"""T03 (LangGraph): the state and its two reducers."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  pytest
from    langgraph.graph                 import  END, START, StateGraph

from    plainedit.graph.state           import  EditState, add_attempts, add_log


#==========================================================================
# T03: the reducers as functions
#==========================================================================
def test_t03_add_attempts_appends_new_attempts() -> None:
    """
    Pin T03: new attempts are appended after the old ones, in order.
    """
    assert add_attempts([], [{"round": 1}]) == [{"round": 1}]
    assert add_attempts([{"round": 1}], [{"round": 2}, {"round": 3}]) == [{"round": 1}, {"round": 2}, {"round": 3}]


#==========================================================================
# T03 add attempts refuses a round that is not after the last
#==========================================================================
def test_t03_add_attempts_refuses_a_round_that_is_not_after_the_last() -> None:
    """
    Pin T03: a repeated or older round raises ValueError (a node ran twice).
    """
    with pytest.raises(ValueError, match="round 2"):
        add_attempts([{"round": 2}], [{"round": 2}])
    with pytest.raises(ValueError):
        add_attempts([{"round": 3}], [{"round": 1}])


#==========================================================================
# T03 add log appends lines
#==========================================================================
def test_t03_add_log_appends_lines() -> None:
    """
    Pin T03: log lines are only ever added.
    """
    assert add_log(["a"], ["b", "c"]) == ["a", "b", "c"]
    assert add_log([], []) == []


#==========================================================================
# T03: the reducers inside a graph
#==========================================================================
def test_t03_a_graph_appends_attempts_and_log_but_replaces_other_keys() -> None:
    """
    Pin T03 in a two-node graph: attempts and log grow, rewrite is replaced.
    """
    def first(state: EditState) -> dict:
        """
        Return attempt 1.

        Input:
            . state         : the state
        Output:
            . update        : one attempt, one log line
        """
        return {"attempts": [{"round": 1}], "log": ["first"], "rewrite": "one"}

    def second(state: EditState) -> dict:
        """
        Return attempt 2.

        Input:
            . state         : the state
        Output:
            . update        : one attempt, one log line
        """
        return {"attempts": [{"round": 2}], "log": ["second"], "rewrite": "two"}

    #----------------------------------------------------------------------
    # Wire and run
    #----------------------------------------------------------------------
    graph = StateGraph(EditState)
    graph.add_node("first", first)
    graph.add_node("second", second)
    graph.add_edge(START, "first")
    graph.add_edge("first", "second")
    graph.add_edge("second", END)
    out = graph.compile().invoke({"draft_id": "X"})
    assert [item["round"] for item in out["attempts"]] == [1, 2]
    assert out["log"] == ["first", "second"] and out["rewrite"] == "two"


#==========================================================================
# The state declares every key the nodes use
#==========================================================================
def test_the_state_declares_every_key_the_nodes_use() -> None:
    """
    Pin the keys of EditState (infrastructure, not a stop).
    """
    keys = set(EditState.__annotations__)
    assert {"draft_id", "original", "facts", "metrics_before", "guidelines", "findings", "attempts", "rewrite",
            "feedback", "rounds", "status", "decision", "log"} <= keys
