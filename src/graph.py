from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from src.state import TechDocState

# TODO: 노드 파일들의 함수/파일 명칭도 아래 import 명칭에 맞춰 추후 업데이트가 필요
from src.nodes.main_node import (
    supervisor_agent,
    context_injection_agent,
    qa_critic_agent,
    final_publish_agent,
    human_approval_agent
)

from src.nodes.sub_graph_nodes.common_node import diagram_analysis_agent, image_placement_agent
from src.nodes.sub_graph_nodes.new_doc_graph_node import (
    new_doc_supervisor_agent,
    structure_planning_agent,
    technical_drafting_agent,
    compliance_editor_agent
)
from src.nodes.sub_graph_nodes.update_doc_graph_node import (
    update_doc_supervisor_agent,
    update_structure_planning_agent,
    update_technical_drafting_agent,
    update_compliance_editor_agent
)


# ==============================================
# 1. 신규 기술 문서를 처리할 Sub-graph (New Doc Graph)
new_doc_workflow = StateGraph(TechDocState)

# intro_워크플로우 node 추가
new_doc_workflow.add_node("new_doc_supervisor", new_doc_supervisor_agent)
new_doc_workflow.add_node("structure_planning", structure_planning_agent)
new_doc_workflow.add_node("technical_drafting", technical_drafting_agent)
new_doc_workflow.add_node("compliance_editor", compliance_editor_agent)
new_doc_workflow.add_node("diagram_analysis", diagram_analysis_agent)
new_doc_workflow.add_node("image_placement", image_placement_agent) # 다이어그램 분석 직후 실행되는 공통 노드

def route_new_doc_graph(state: TechDocState):
    step = state.get('sub_next_step')
    return step

# new_doc 워크플로우 순서
new_doc_workflow.add_edge(START, "new_doc_supervisor")

new_doc_workflow.add_conditional_edges("new_doc_supervisor", route_new_doc_graph,
                                     {
                                        'structure_planning': 'structure_planning',
                                        'technical_drafting': 'technical_drafting',
                                        "diagram_analysis": "diagram_analysis",
                                        "compliance_editor": "compliance_editor",
                                        "end": END
                                    })

new_doc_workflow.add_edge("diagram_analysis", "image_placement") # 분석 끝나면 삽입으로

new_doc_workflow.add_edge("structure_planning", "new_doc_supervisor")
new_doc_workflow.add_edge("image_placement", "new_doc_supervisor")
new_doc_workflow.add_edge("technical_drafting", "new_doc_supervisor")
new_doc_workflow.add_edge("compliance_editor", "new_doc_supervisor")

new_doc_app = new_doc_workflow.compile()
# ==============================================


# ==============================================
# 2. 업데이트 기술 문서를 처리할 Sub-graph (Update Doc Graph)

update_doc_workflow = StateGraph(TechDocState)

# update_doc_workflow node 추가
update_doc_workflow.add_node("update_doc_supervisor", update_doc_supervisor_agent)
update_doc_workflow.add_node("structure_planning", update_structure_planning_agent)
update_doc_workflow.add_node("diagram_analysis", diagram_analysis_agent)
update_doc_workflow.add_node("technical_drafting", update_technical_drafting_agent)
update_doc_workflow.add_node("compliance_editor", update_compliance_editor_agent)
update_doc_workflow.add_node("image_placement", image_placement_agent)


def route_update_doc_graph(state: TechDocState):
    step = state.get('sub_next_step')
    return step

# update_doc_workflow 순서
update_doc_workflow.add_edge(START, "update_doc_supervisor")

update_doc_workflow.add_conditional_edges('update_doc_supervisor', route_update_doc_graph,
                                            {
                                                "structure_planning": "structure_planning",
                                                "diagram_analysis": "diagram_analysis",
                                                "technical_drafting": "technical_drafting",
                                                "compliance_editor": "compliance_editor",
                                                "end": END
                                        })

update_doc_workflow.add_edge("diagram_analysis", "image_placement")

update_doc_workflow.add_edge("structure_planning", "update_doc_supervisor")
update_doc_workflow.add_edge("image_placement", "update_doc_supervisor")
update_doc_workflow.add_edge("technical_drafting", "update_doc_supervisor")
update_doc_workflow.add_edge("compliance_editor", "update_doc_supervisor")

update_doc_app = update_doc_workflow.compile()
# ==============================================

# ==============================================
# 3. Main 워크플로우 (전체 오케스트레이션)
workflow = StateGraph(TechDocState)

workflow.add_node('supervisor', supervisor_agent)
workflow.add_node('context_injection', context_injection_agent)
workflow.add_node('new_doc_graph', new_doc_app) # 서브 그래프를 노드로 넣는다.
workflow.add_node('update_doc_graph', update_doc_app) # 서브 그래프를 노드로 넣는다.
workflow.add_node('qa_critic', qa_critic_agent)
workflow.add_node('human_approval', human_approval_agent)
workflow.add_node('final_publish', final_publish_agent)

workflow.add_edge(START, 'supervisor')

def route_from_supervisor(state: TechDocState) -> str:
    # 아직은 supervisor_agent가 state의 'next_step'을 업데이트 했다고 가정
    return state.get('next_step')

workflow.add_conditional_edges('supervisor', route_from_supervisor,
                               {'context_injection' : 'context_injection',
                                'new_doc_graph' : 'new_doc_graph',
                                'update_doc_graph': 'update_doc_graph',
                                'qa_critic' : 'qa_critic',
                                'human_approval': 'human_approval',
                                'final_publish': 'final_publish',
                                   })

workflow.add_edge('context_injection', 'supervisor')
workflow.add_edge('new_doc_graph', 'supervisor')
workflow.add_edge('update_doc_graph', 'supervisor')
workflow.add_edge('qa_critic', 'supervisor')

workflow.add_edge('human_approval', 'supervisor')
workflow.add_edge('final_publish', END)

memory = MemorySaver()

app = workflow.compile(
    checkpointer= memory,
    interrupt_before= ['human_approval']
)

# # 컴파일된 app 객체 사용
# https://mermaid.live 이 사이트에 출력된 결롸를 넣으면 시각화 그래프를 얻을 수 잇다.

# print(app.get_graph().draw_mermaid())
# print(new_doc_app.get_graph().draw_mermaid())
# print(update_doc_app.get_graph().draw_mermaid())