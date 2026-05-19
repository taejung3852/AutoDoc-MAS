from langchain_upstage import UpstageDocumentParseLoader
from src.state import TechDocState
import re

def data_ingest_supervisor_agent(state: TechDocState):
    """
    data_ingest_graph의 supervisor 에이전트.
    현재 data_ingest_next_step 상태 값을 보고 다음 노드를 결정한다.
    """
    file_type = state.get('file_type')
    technical_source = state.get('technical_source')
    parser_verdict = state.get('parser_verdict')         # 검증 실패 메시지

    # 만약에 초기라면
    if not technical_source:
        if file_type == 'pdf':
            return {'data_ingest_next_step': 'pdf_parser'}
        else:
            return {'data_ingest_next_step': 'text_cleaner'}
    
    if not parser_verdict:
        return {'data_ingest_next_step': 'parse_validator'}

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

    return {"technical_source": parsed_text}


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
    content = state.get('technical_source')

    # 빈 문자열 판단
    if not content or not content.strip():
        return {"parser_verdict": "FAIL"}

    # 인코딩 깨짐 의심 (대체 문자 U+FFFD 다수 등장)
    if content.count('\ufffd') > 10:
        return {"parser_verdict": "FAIL"}

    return {"parser_verdict": "PASS"}