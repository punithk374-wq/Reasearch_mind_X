from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.extraction_service import get_paper_summary
from app.services.gap_service import detect_gaps
from app.services.verification_service import verify_gaps_batch


# One shared state dictionary flows through every step
class WorkflowState(TypedDict):
    user_id: int
    paper_ids: list[int]
    titles: dict[int, str]
    summaries: list[dict]
    gaps: list[dict]
    note: str | None
    verifications: list[dict]
    verified_gaps: list[dict]
    dropped: list[dict]
    report: dict
    trace: list[str]


def extract_summaries(state: WorkflowState) -> dict:
    summaries = []
    for pid in state["paper_ids"]:
        summary = dict(get_paper_summary(pid, state["user_id"]))
        summary["paper_id"] = pid
        summary["title"] = state["titles"][pid]
        summaries.append(summary)
    return {
        "summaries": summaries,
        "trace": state["trace"] + [f"Extract: summarised {len(summaries)} papers"],
    }


def find_gaps(state: WorkflowState) -> dict:
    result = detect_gaps(state["summaries"])
    gaps = result["gaps"]
    return {
        "gaps": gaps,
        "note": result.get("note") or None,
        "trace": state["trace"] + [f"Detect: found {len(gaps)} candidate gaps"],
    }


def verify_evidence(state: WorkflowState) -> dict:
    verifications = verify_gaps_batch(state["gaps"], state["user_id"])
    return {
        "verifications": verifications,
        "trace": state["trace"] + ["Verify: checked each gap against the paper text"],
    }


STATUS_LABELS = {
    "supported": "verified",
    "partial": "partially verified",
    "unverified": "unverified",
}


def triage(state: WorkflowState) -> dict:
    """Decision step: drop gaps the papers do not support, flag the weaker ones."""
    kept, dropped = [], []
    for gap, ver in zip(state["gaps"], state["verifications"]):
        item = {
            **gap,
            "verdict": ver["verdict"],
            "status": STATUS_LABELS.get(ver["verdict"], "unsupported"),
            "verified_paper_ids": ver["supported_paper_ids"],
            "verification_reason": ver["reason"],
            "passages": [
                {**p, "text": p["text"][:500]} for p in ver["passages"]
            ],
        }
        (dropped if ver["verdict"] == "unsupported" else kept).append(item)
    return {
        "verified_gaps": kept,
        "dropped": dropped,
        "trace": state["trace"]
        + [f"Triage: kept {len(kept)}, dropped {len(dropped)} unsupported"],
    }


def write_report(state: WorkflowState) -> dict:
    report = {
        "papers": [
            {"paper_id": pid, "title": state["titles"][pid]}
            for pid in state["paper_ids"]
        ],
        "gaps": state["verified_gaps"],
        "dropped_count": len(state["dropped"]),
        "note": state["note"],
        "trace": state["trace"] + ["Report: assembled"],
    }
    return {"report": report}


def after_detect(state: WorkflowState) -> str:
    """Conditional edge: no gaps means there is nothing to verify."""
    return "verify_evidence" if state["gaps"] else "write_report"


# Note: node names must differ from state keys, so none of these is called
# "report" or "gaps".
graph = StateGraph(WorkflowState)
graph.add_node("extract_summaries", extract_summaries)
graph.add_node("find_gaps", find_gaps)
graph.add_node("verify_evidence", verify_evidence)
graph.add_node("triage", triage)
graph.add_node("write_report", write_report)

graph.add_edge(START, "extract_summaries")
graph.add_edge("extract_summaries", "find_gaps")
graph.add_conditional_edges(
    "find_gaps",
    after_detect,
    {"verify_evidence": "verify_evidence", "write_report": "write_report"},
)
graph.add_edge("verify_evidence", "triage")
graph.add_edge("triage", "write_report")
graph.add_edge("write_report", END)

workflow = graph.compile()


def run_workflow(paper_ids: list[int], titles: dict[int, str], user_id: int) -> dict:
    final = workflow.invoke(
        {
            "user_id": user_id,
            "paper_ids": paper_ids,
            "titles": titles,
            "summaries": [],
            "gaps": [],
            "note": None,
            "verifications": [],
            "verified_gaps": [],
            "dropped": [],
            "report": {},
            "trace": [],
        }
    )
    return final["report"]