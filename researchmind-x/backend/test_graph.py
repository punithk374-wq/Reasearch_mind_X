from typing import TypedDict

from langgraph.graph import END, START, StateGraph


# The shared state every node can read from and add to
class State(TypedDict):
    text: str
    steps: list[str]


def node_a(state: State) -> dict:
    return {"steps": state["steps"] + ["a ran"]}


def node_b(state: State) -> dict:
    return {"steps": state["steps"] + ["b ran"]}


graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge(START, "a")
graph.add_edge("a", "b")
graph.add_edge("b", END)

app = graph.compile()
print(app.invoke({"text": "hi", "steps": []}))