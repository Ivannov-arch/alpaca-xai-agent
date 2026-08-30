"""
graph.py — Assembles the LangGraph state machine.

Node wiring:
  START
    └─► formulate_hypothesis (Phase 1)
           │
           ├─ [error] ──────────────────────────────► END (aborted)
           │
           └─ [ok] ─────────────────────────────────► execute_order (Phase 2)
                                                             │
                                                             └──────────────► END
                                                             (monitoring worker takes
                                                              over from here onward)

  Worker re-entry per ACTIVE hypothesis:
    START (audit trigger)
      └─► audit_position (Phase 3)
             │
             ├─ [HOLD]  ──────────────────────────────► END (wait for next cycle)
             │
             └─ [CLOSE] ──────────────────────────────► close_and_post_mortem (Phase 4)
                                                               │
                                                               └─────────────────► END

Imports from:
  - state.py  (AgentState TypedDict)
  - nodes/phase1_hypothesis.py
  - nodes/phase2_execution.py
  - nodes/phase3_audit.py
  - nodes/phase4_postmortem.py
"""
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.phase1_hypothesis import phase1_formulate_hypothesis
from agent.nodes.phase2_execution import phase2_execute_order
from agent.nodes.phase3_audit import phase3_audit_position
from agent.nodes.phase4_postmortem import phase4_post_mortem


def _route_after_phase1(state: AgentState) -> str:
    """Abort if Phase 1 sets an error, otherwise proceed to execution."""
    if state.get("error"):
        return "abort"
    return "execute"


def _route_after_phase3(state: AgentState) -> str:
    """Close the position if audit says CLOSE, otherwise hold until next cycle."""
    if state.get("audit_verdict") == "CLOSE":
        return "close"
    return "hold"


def build_trade_graph() -> StateGraph:
    """
    Phase 1 → 2 graph: triggered manually via API when starting a new trade.
    """
    graph = StateGraph(AgentState)

    graph.add_node("formulate_hypothesis", phase1_formulate_hypothesis)
    graph.add_node("execute_order", phase2_execute_order)

    graph.set_entry_point("formulate_hypothesis")
    graph.add_conditional_edges(
        "formulate_hypothesis",
        _route_after_phase1,
        {"execute": "execute_order", "abort": END},
    )
    graph.add_edge("execute_order", END)

    return graph.compile()


def build_audit_graph() -> StateGraph:
    """
    Phase 3 → 4 graph: triggered by the background worker every N minutes.
    """
    graph = StateGraph(AgentState)

    graph.add_node("audit_position", phase3_audit_position)
    graph.add_node("close_and_post_mortem", phase4_post_mortem)

    graph.set_entry_point("audit_position")
    graph.add_conditional_edges(
        "audit_position",
        _route_after_phase3,
        {"close": "close_and_post_mortem", "hold": END},
    )
    graph.add_edge("close_and_post_mortem", END)

    return graph.compile()


# Pre-compiled graphs — imported by api/routes and worker.py
trade_graph = build_trade_graph()
audit_graph = build_audit_graph()
