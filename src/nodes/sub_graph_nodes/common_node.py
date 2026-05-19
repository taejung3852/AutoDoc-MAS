from src.utils import encode_image_to_base64, critic_llm
from src.state import TechDocState
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

load_dotenv()

def diagram_analysis_agent(state: TechDocState) -> dict:
    print("\n[Node: Diagram Analysis] 첨부된 아키텍처 다이어그램의 시각적 요소를 분석합니다...")
    
    image_paths = state.get('captured_diagrams', [])
    if not image_paths:
        return {"diagram_analysis_result": "첨부된 이미지 없음"}

    base64_images = []
    file_names = []
    for path in image_paths:
        encoded = encode_image_to_base64(path)
        if encoded:
            base64_images.append(encoded)
            file_names.append(os.path.basename(path))

    if not base64_images:
        return {"diagram_analysis_result": "유효한 다이어그램 파일이 없습니다."}
    
    file_names_str = "\n".join(file_names)
    print(f"  -> {len(base64_images)}개의 다이어그램을 분석 중...")

    # 프롬프트: 철저하게 캡셔닝(Captioning)만 지시
    sys_msg = f"""
    # Role
    당신은 복잡한 시스템 아키텍처와 ERD를 판독하는 수석 시스템 비전 분석가(Vision Analyst)입니다.

    # Instructions
    제공된 다이어그램(이미지)들을 관찰하고, 각 다이어그램이 나타내는 시스템의 구조, 컴포넌트 간의 상호작용, 또는 데이터 흐름을 텍스트로 명확히 분석하십시오.

    # Steps
    1. 다이어그램 내에 존재하는 모든 텍스트, 시스템 노드(Node), 그리고 데이터베이스 엔티티(Entity)를 식별하십시오.
    2. 노드 간의 연결선(Edge)과 화살표 방향을 추적하여 컴포넌트 간의 의존성 및 데이터 흐름의 순서를 파악하십시오.
    3. 파악된 시각적 정보를 종합하여, 텍스트만으로도 이미지가 그려지도록 핵심 요약본을 작성하십시오.

    # Expectations
    이 분석 결과는 눈이 보이지 않는 후속 에이전트(테크니컬 라이터)가 기술 문서 본문을 작성할 때 시각 자료를 정확히 설명하기 위한 '대체 텍스트(Context)'로 사용됩니다. 따라서 누락이나 왜곡 없는 철저한 팩트 기반의 명세가 필요합니다.

    # Narrowing
    - 절대 이미지에 명시되지 않은 아키텍처, DB 테이블, 기능 등을 배경 지식으로 유추하여 지어내지 마십시오. 오직 이미지에 존재하는 텍스트와 연결선만 분석하십시오.
    - 부가적인 인사말이나 감성적인 코멘트를 절대 포함하지 마십시오.
    - 각 파일명과 분석 내역을 1:1로 매핑하여 반드시 아래의 [Format] 구조로만 출력하십시오.

    [Format]
    - [파일명]: (핵심 컴포넌트 및 데이터 흐름 요약 2~3문장)
    - [파일명]: (핵심 컴포넌트 및 데이터 흐름 요약 2~3문장)
    """

    content_parts = [{"type": "text", "text": f"첨부된 이미지 파일명: {file_names_str}"}] # 휴먼 메시지로 들어갈 내용이다.
    
    for b64_img in base64_images:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })

    response = critic_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=content_parts)
    ])

    print("  -> ✅ 다이어그램 분석 완료.")
    return {"diagram_analysis_result": response.content}

def image_placement_agent(state: TechDocState) -> dict:
    print("\n[Node: Image Placement] 분석된 다이어그램을 기술 문서 본문의 적절한 위치에 삽입합니다...")
    
    guide = state.get("diagram_analysis_result")
    draft = state.get("tech_reviewed_content")

    # 이미지가 없거나 분석되지 않았다면 패스
    if not guide or guide == "첨부된 다이어그램 없음":
        return {}

    sys_msg = """
    ### 1. Role
    당신은 기술 문서의 시각적 가독성을 높이고 데이터를 적절히 배치하는 수석 테크니컬 퍼블리셔입니다.

    ### 2. Instructions
    '다이어그램 분석 내역'을 바탕으로, '원본 기술 문서' 내에서 해당 다이어그램이 설명되는 가장 논리적인 위치(문단 사이)에 다이어그램 삽입 마커를 배치하십시오.

    ### 3. Steps
    1. 다이어그램 분석 내역을 읽고 각 다이어그램(이미지)이 설명하는 핵심 아키텍처나 컴포넌트를 파악하십시오.
    2. 원본 기술 문서를 정독하며, 해당 다이어그램의 설명이 시작되기 직전이나 직후의 가장 자연스러운 문단 간격을 찾으십시오.
    3. 찾은 위치에 개행(Enter)을 추가하고 지정된 마커를 삽입하십시오.

    ### 4. Expectations
    독자가 문서를 읽어 내려갈 때, 텍스트의 설명과 시각적 다이어그램이 완벽한 타이밍에 매칭되어 시스템에 대한 이해도를 극대화해야 합니다.

    ### 5. Narrowing
    - 절대 원본 문서의 기술적 사실, 문장, 단어를 단 한 글자도 임의로 수정하거나 삭제하지 마십시오.
    - 마커는 반드시 별도의 줄(개행)에 독립적으로 작성되어야 합니다.

    [Format]
    (기존 기술 문서 텍스트)
    
    (기존 기술 문서 텍스트)

    """

    human_msg = f"""
    [다이어그램 분석 내역]
    {guide}
    
    [원본 기술 문서 (교정 완료본)]
    {draft}
    """
    
    response = critic_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])

    print("  -> ✅ 다이어그램 삽입 마커 배치 완료.")
    # 마커가 추가된 글로 덮어씌움
    return {"tech_reviewed_content": response.content}