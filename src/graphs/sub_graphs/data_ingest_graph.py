from langgraph.graph import StateGraph, START, END
from src.state import TechDocState
from src.nodes.sub_graph_nodes.data_ingest_graph_node import (
    data_ingest_supervisor_agent,
    pdf_parser_agent,
    text_cleaner_agent,
    parser_validator_agent,
    figure_analyzer_agent
)


# ==========================================
# 조건부 엣지: supervisor 판단 결과에 따라 라우팅
# ==========================================
def route_from_supervisor(state: TechDocState) -> str:
    return state.get("data_ingest_next_step", "end")


# ==========================================
# data_ingest_graph 빌드
# ==========================================
workflow = StateGraph(TechDocState)

# 노드 등록
workflow.add_node("data_ingest_supervisor", data_ingest_supervisor_agent)
workflow.add_node("pdf_parser", pdf_parser_agent)
workflow.add_node("text_cleaner", text_cleaner_agent)
workflow.add_node("parser_validator", parser_validator_agent)
workflow.add_node("figure_analyzer", figure_analyzer_agent)

# 엣지 연결
workflow.add_edge(START, "data_ingest_supervisor")

workflow.add_conditional_edges(
    "data_ingest_supervisor",
    route_from_supervisor,
    {
        "pdf_parser": "pdf_parser",
        "text_cleaner": "text_cleaner",
        "parser_validator": "parser_validator",
        "figure_analyzer": "figure_analyzer",
        "end": END,
    }
)

# 각 작업 노드 완료 후 → supervisor로 복귀
workflow.add_edge("pdf_parser", "data_ingest_supervisor")
workflow.add_edge("text_cleaner", "data_ingest_supervisor")
workflow.add_edge("parser_validator", "data_ingest_supervisor")
workflow.add_edge("figure_analyzer", "data_ingest_supervisor")

data_ingest_graph = workflow.compile()