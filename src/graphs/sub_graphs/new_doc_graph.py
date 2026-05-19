from langgraph.graph import StateGraph, START, END
from src.state import TechDocState
from src.nodes.sub_graph_nodes.common_node import diagram_analysis_agent, image_placement_agent
from src.nodes.sub_graph_nodes.new_doc_graph_node import (
    new_doc_supervisor_agent,
    structure_planning_agent,
    technical_drafting_agent,
    compliance_editor_agent
)

def route_from_supervisor(state: TechDocState) -> str:
    return state.get('sub_next_step')

workflow = StateGraph(TechDocState)

workflow.add_node("new_doc_supervisor", new_doc_supervisor_agent)
workflow.add_node("structure_planning", structure_planning_agent)
workflow.add_node("technical_drafting", technical_drafting_agent)
workflow.add_node("compliance_editor", compliance_editor_agent)
workflow.add_node("diagram_analysis", diagram_analysis_agent)
workflow.add_node("image_placement", image_placement_agent)

workflow.add_edge(START, "new_doc_supervisor")

workflow.add_conditional_edges("new_doc_supervisor", route_from_supervisor,
                               {
                                   "structure_planning": "structure_planning",
                                    "technical_drafting": "technical_drafting",
                                    "diagram_analysis": "diagram_analysis",
                                    "compliance_editor": "compliance_editor",
                                    "end": END,
                               })

workflow.add_edge("diagram_analysis", "image_placement") # 분석 끝나면 삽입으로

workflow.add_edge("structure_planning", "new_doc_supervisor")
workflow.add_edge("image_placement", "new_doc_supervisor")
workflow.add_edge("technical_drafting", "new_doc_supervisor")
workflow.add_edge("compliance_editor", "new_doc_supervisor")

new_doc_app = workflow.compile()