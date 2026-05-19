from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from src.state import TechDocState
from src.nodes.main_node import (
    supervisor_agent,
    qa_critic_agent,
    final_publish_agent,
    human_approval_agent
)
from src.graphs.sub_graphs.data_ingest_graph import data_ingest_graph
from src.graphs.sub_graphs.new_doc_graph import new_doc_graph
from src.graphs.sub_graphs.update_doc_graph import update_doc_graph

def route_from_supervisor(state: TechDocState) -> str:
    # 아직은 supervisor_agent가 state의 'next_step'을 업데이트 했다고 가정
    return state.get('next_step')

workflow = StateGraph(TechDocState)

workflow.add_node('supervisor', supervisor_agent)
workflow.add_node('new_doc_graph', new_doc_graph)
workflow.add_node('update_doc_graph', update_doc_graph)
workflow.add_node('data_ingest_graph', data_ingest_graph)
workflow.add_node('qa_critic', qa_critic_agent)
workflow.add_node('human_approval', human_approval_agent)
workflow.add_node('final_publish', final_publish_agent)

workflow.add_edge(START, 'supervisor')



workflow.add_conditional_edges('supervisor', route_from_supervisor,
                               {
                                    'data_ingest_graph' : 'data_ingest_graph',
                                    'new_doc_graph' : 'new_doc_graph',
                                    'update_doc_graph': 'update_doc_graph',
                                    'qa_critic' : 'qa_critic',
                                    'human_approval': 'human_approval',
                                    'final_publish': 'final_publish',
                                })

workflow.add_edge('data_ingest_graph', 'supervisor')
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