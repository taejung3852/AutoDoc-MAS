from langchain_core.messages import SystemMessage, HumanMessage
from langchain_upstage import UpstageDocumentParseLoader
from src.state import TechDocState
from src.utils import critic_llm
import re

def data_ingest_supervisor_agent(state: TechDocState):
    """
    data_ingest_graph의 supervisor 에이전트.
    현재 data_ingest_next_step 상태 값을 보고 다음 노드를 결정한다.
    """
    file_type = state.get('file_type')
    technical_source = state.get('technical_source')
    parser_verdict = state.get('parser_verdict')         
    pdf_extracted_figures = state.get('pdf_extracted_figures')

    # 만약에 초기라면
    if not technical_source:
        if file_type == 'pdf':
            return {'data_ingest_next_step': 'pdf_parser'}
        else:
            return {'data_ingest_next_step': 'text_cleaner'}
    
    if pdf_extracted_figures:
        return {'data_ingest_next_step': 'figure_analyzer'}

    if not parser_verdict:
        return {'data_ingest_next_step': 'parser_validator'}

    # === 판단을 main 그래프의 supervisor에서 여기서 parser_verdict의 여부를 나눠서 반환이 의미 없지만 가독성? 때문에 뒀다. ===
    if parser_verdict == "PASS":
        return {'data_ingest_next_step': 'end'}
    
    if parser_verdict == 'FAIL':
        return {'data_ingest_next_step': 'end'}
    
    return {'data_ingest_next_step': 'end'}

def pdf_parser_agent(state: TechDocState):
    """
    Upstage Document Parse API를 사용해 PDF를 텍스트로 변환한다.
    """
    print("[Node: PDF Parser] Upstage Document Parse API 호출 중...")
    raw_file_path = state.get('raw_file_path')

    loader = UpstageDocumentParseLoader(
        file_path=raw_file_path,
        output_format="html",
        split="element", # 페이지 보다는 RAG 청킹에 더 유리할 것으로 보인다.
        ocr = "auto",
        chart_recognition= True,
        base64_encoding=['figure', 'chart']
    )

    docs = loader.load() # 페이지별로 html 언어(문자열)로 나눠져 있을 것이다.
    parsed_text = '\n\n'.join([doc.page_content for doc in docs])

    # base64 이미지 추출
    figures = [
            b64 for doc in docs
            if (b64 := doc.metadata.get("base64_encoding")) and b64.strip()
        ]

    print(f"  -> 텍스트 파싱 완료. 추출된 figure/chart: {len(figures)}개")

    return {
        "technical_source": parsed_text,
        "pdf_extracted_figures": figures if figures else None
    }

def figure_analyzer_agent(state: TechDocState) -> dict:
    print("[Node: Figure Analyzer] PDF 추출 figure/chart Vision 분석 중...")
    figures = state.get('pdf_extracted_figures', [])
    technical_source = state.get('technical_source', '')

    content_parts = [{"type": "text", "text": "아래 이미지들은 PDF에서 추출된 figure/chart입니다. 각 이미지에 담긴 데이터, 수치, 구조를 텍스트로 상세히 설명하십시오."}]

    for b64 in figures:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })

    sys_msg = """
    # Role 
    당신은 IT 엔터프라이즈 환경에서 기술 문서 내 시각 데이터(아키텍처 다이어그램, 차트, 순서도 등)를 정밀하게 해독하고 텍스트로 구조화하는 10년 차 수석 Vision 데이터 분석가입니다.

    # Instructions 
    목표: 제공된 시각 데이터를 분석하여, 그 안에 담긴 객관적 수치, 구성 요소, 관계성 및 흐름을 누락 없이 정확한 텍스트로 변환하는 것입니다.
    맥락: 추출된 텍스트는 이후 기술 문서 초안 작성을 위한 핵심 소스로 병합되므로, 시각적 정보의 텍스트화 손실이 없어야 합니다.

    # Steps 
    1. 제공된 이미지의 전체적인 맥락과 유형(예: 트래픽 차트, 결제 시스템 아키텍처, ERD 등)을 파악하여 구조의 틀을 잡으십시오.
    2. 이미지 내에 포함된 모든 텍스트, 숫자(수치/비율), 범례, 노드(Node) 및 엣지(Edge/화살표)의 방향성을 빠짐없이 추출하십시오.
    3. 추출된 요소를 바탕으로 데이터의 흐름, 시스템 간의 관계, 핵심 지표를 논리적이고 구조화된 문장 및 리스트로 정리하십시오.

    # Expectations
    - 이미지를 전혀 보지 못한 개발자나 엔지니어가 당신의 텍스트만 읽고도 해당 도표나 차트의 구조와 수치를 완벽하게 머릿속에 그릴 수 있을 만큼 상세하고 명확해야 합니다.
    - 분석된 텍스트는 자동화된 기술 문서 파이프라인의 기초 자료로 즉시 복사-붙여넣기 할 수 있는 수준의 정보 밀도와 가독성을 갖춰야 합니다.

    # Narrowing
    - 항상 여러 이미지가 제공될 경우, 각 이미지별로 명확한 헤딩(예: `### Figure 1 분석`, `### Figure 2 분석`)을 두어 개별적으로 서술하십시오.
    - 절대 이미지에 명시되지 않은 수치, 배경지식, 외부 정보, 시스템 동작 원리를 임의로 유추하거나 창작(Hallucination)하여 서술하지 마십시오. 오직 시각적으로 확인되는 정보만 다루십시오.
    - 절대 인사말, 서론, "분석 결과입니다"와 같은 대화형 코멘트를 포함하지 마십시오.
    - 결과물은 반드시 가독성을 위해 마크다운(Markdown) 형식(리스트, 표 등 활용)으로 구조화하여 단독으로 출력하십시오.
    """

    
    response = critic_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=content_parts)
    ])

    if isinstance(response.content, str):
        figure_description = response.content
    elif isinstance(response.content, list):
        figure_description = "\n".join(
            item["text"] for item in response.content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    else:
        figure_description = str(response.content)

    print(f"  -> ✅ Figure 분석 완료. technical_source에 합칩니다.")

    merged_source = technical_source + "\n\n[PDF 추출 Figure/Chart 분석]\n" + figure_description

    return {
        "technical_source": merged_source,
        "pdf_extracted_figures": None   # 처리 완료 후 리셋
    }

def text_cleaner_agent(state: TechDocState):
    """
    텍스트 입력의 노이즈를 제거!
    (연속 줄바꿈, 줄 앞뒤 공백, 연속 공백 정리)
    """
    raw_text = state.get('technical_source')

    # 3줄 이상 연속 줄바꿈 -> 2줄로 압축
    cleaned = re.sub(r'\n{3,}', '\n\n', raw_text)
    # 줄 앞뒤 공백 제거
    cleaned = '\n'.join([line.strip() for line in cleaned.splitlines()])
    # 연속 공백 앞축
    cleaned = re.sub(r' {2,}', ' ', cleaned)

    return {"technical_source": cleaned}


def parser_validator_agent(state: TechDocState):
    """
    파싱/클리닝 결과물의 최소 품질 기준을 검증한다.
    기준 미달 시 ValueError를 발생시켜 파이프라인을 중단한다.

    LLM 사용안하고 판단. 
    """
    print("[Node: Parse Validator] 파싱 결과 품질 검증 중...")
    content = state.get('technical_source')

    # 빈 문자열 판단
    if not content or not content.strip():
        return {"parser_verdict": "FAIL"}

    # 인코딩 깨짐 의심 (대체 문자 U+FFFD 다수 등장)
    if content.count('\ufffd') > 10:
        return {"parser_verdict": "FAIL"}

    return {"parser_verdict": "PASS"}