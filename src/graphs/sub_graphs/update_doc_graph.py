from langgraph.graph import StateGraph, START, END
from src.state import TechDocState
from src.nodes.sub_graph_nodes.common_node import diagram_analysis_agent, image_placement_agent
from src.nodes.sub_graph_nodes.update_doc_graph_node import (
    update_doc_supervisor_agent,
    update_structure_planning_agent,
    update_technical_drafting_agent,
    update_compliance_editor_agent,
    context_injection_agent
)


def route_from_supervisor(state: TechDocState) -> str:
    return state.get('sub_next_step')


workflow = StateGraph(TechDocState)

workflow.add_node("update_doc_supervisor", update_doc_supervisor_agent)
workflow.add_node("context_injection", context_injection_agent)
workflow.add_node("structure_planning", update_structure_planning_agent)
workflow.add_node("technical_drafting", update_technical_drafting_agent)
workflow.add_node("compliance_editor", update_compliance_editor_agent)
workflow.add_node("diagram_analysis", diagram_analysis_agent)
workflow.add_node("image_placement", image_placement_agent)

workflow.add_edge(START, "update_doc_supervisor")

workflow.add_conditional_edges(
    "update_doc_supervisor",
    route_from_supervisor,
    {
        "context_injection": "context_injection",
        "structure_planning": "structure_planning",
        "diagram_analysis": "diagram_analysis",
        "technical_drafting": "technical_drafting",
        "compliance_editor": "compliance_editor",
        "end": END,
    }
)

workflow.add_edge("diagram_analysis", "image_placement")
workflow.add_edge('context_injection', 'update_doc_supervisor')
workflow.add_edge("structure_planning", "update_doc_supervisor")
workflow.add_edge("image_placement", "update_doc_supervisor")
workflow.add_edge("technical_drafting", "update_doc_supervisor")
workflow.add_edge("compliance_editor", "update_doc_supervisor")

update_doc_graph = workflow.compile()