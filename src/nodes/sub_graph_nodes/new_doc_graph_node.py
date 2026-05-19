from langchain_core.messages import SystemMessage, HumanMessage
from src.state import TechDocState
from src.utils import writer_llm, critic_llm

# ==============================================
# Supervisor 에이전트
def new_doc_supervisor_agent(state: TechDocState) -> dict:
    print("\n[Node: New Doc Supervisor] 신규 문서 작성 부서 작업 지시 중...")

    technical_source = state.get("technical_source")
    doc_outline = state.get("doc_outline")
    doc_draft = state.get("doc_draft")
    tech_reviewed_content = state.get("tech_reviewed_content")
    captured_diagrams = state.get("captured_diagrams")
    diagram_analysis_result = state.get("diagram_analysis_result")

    if not technical_source: # 이게 블로그를 작성하는 핵심 소스라서 서브 그래프에서도 한번 더 판단
        print("  -> ⚠️ 경고: 기술 자료가 없습니다. 메인으로 복귀합니다.")
        return {"sub_next_step": "end"}
    
    # State에 값이 채워져 있는지 확인하여 다음 단계를 지정
    if not doc_outline:
        next_step = "structure_planning"
    elif not doc_draft:
        next_step = "technical_drafting"
    elif not tech_reviewed_content:
        next_step = "compliance_editor"
    elif captured_diagrams and not diagram_analysis_result:
        next_step = "diagram_analysis"
    else:
        print("  -> 서브 그래프 작업 완료! 메인 Supervisor로 복귀합니다.")
        return{'sub_next_step':'end'}
        
    return {"sub_next_step": next_step}

# ==============================================
# 아웃라인 작성 에이전트
def structure_planning_agent(state: TechDocState) -> dict:
    print("[Node: Structure Planning] 기술 문서 아웃라인 설계 중...")
    system_name = state.get('system_name')
    technical_source = state.get('technical_source')
    
    # 첫 포스팅 전용 프롬프트: 새로운 주제 시작에 집중
    sys_msg = f"""
    # Role
    당신은 기업의 시스템 아키텍처와 명세서를 기획하는 수석 테크니컬 기획자(Technical Planner)입니다.

    # Instructions
    제공된 원시 기술 데이터를 분석하여, 논리적이고 체계적인 기술 문서의 목차(Outline)를 설계하십시오.

    # Steps
    1. 원시 데이터에서 핵심 기능, 시스템 목적, 제약 사항 등 주요 엔티티를 식별하십시오.
    2. 기술 문서의 표준 흐름(개요 -> 아키텍처/기능 -> 상세 명세 -> 결론/고려사항)에 맞게 뼈대를 구성하십시오.
    3. 각 목차가 어떤 내용을 담을지 1줄 요약으로 명시하십시오.

    # Expectations
    개발자가 이 목차만 보더라도 시스템의 전체 구조와 데이터 흐름을 직관적으로 파악할 수 있어야 합니다.

    # Narrowing
    - 절대 본문 내용(Body Text)을 길게 작성하지 마십시오. 오직 마크다운 헤딩(#, ##)과 Bullet Point만 사용하십시오.
    - 백과사전식 나열을 피하고, 시스템의 논리적 흐름에 집중하십시오.
    """

    human_msg = f"""
    [문서화 대상 시스템명]
    {system_name}

    [기술 데이터]
    {technical_source}
    """
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return {"doc_outline": response.content}

# ==============================================
# 초안작성 에이전트
def technical_drafting_agent(state: TechDocState) -> dict:
    print("[Node: Technical Drafting] 기술 문서 초안 작성 중...")

    qa_feedback = state.get('qa_feedback')
    system_name = state.get('system_name')
    doc_style_guide = state.get('doc_style_guide')
    doc_outline = state.get('doc_outline')
    technical_source = state.get('technical_source')
    
    # 1편 전용 프롬프트: 첫인상과 배경 설명에 집중
    sys_msg = """
    # Role
    당신은 원시 기술 데이터를 객관적인 명세서로 변환하는 엄격한 테크니컬 라이터입니다.

    # Instructions
    기획된 아웃라인과 사내 작성 가이드라인을 기반으로, 원시 기술 데이터(슬랙, 회의록 등)에 명시된 팩트만을 사용하여 기술 문서 초안을 작성하십시오.

    # Steps
    1. 아웃라인의 목차를 전개하되, '원시 기술 데이터'와 한 줄씩 대조하며 작성하십시오.
    2. 원시 데이터에 존재하는 팩트(API 경로, 파라미터, DB 테이블명, 타임아웃 등)만 해당 목차에 배치하십시오.
    3. 사내 작성 가이드라인(어조, 포맷팅 등)을 적용하여 문장을 건조하게 다듬으십시오.

    # Expectations
    당신의 유일한 임무는 '데이터의 규격화'입니다. 제공된 대화나 메모에 없는 시스템의 목적, 데이터 흐름, 향후 고려사항 등을 절대 유추해서는 안 됩니다.

    # Narrowing
    - [Hallucination 절대 금지] 원시 데이터에 언급되지 않은 기술적 팩트나 로직(예: 트랜잭션, 모니터링 등)을 LLM의 배경 지식으로 임의 창작하여 덧붙이는 행위를 엄격히 금지합니다.
    - 아웃라인(목차)이 존재하더라도, 원시 데이터에서 채울 내용이 없다면 그럴듯하게 문장을 지어내지 말고 해당 목차를 생략하거나 "내용 없음"으로 처리하십시오.
    - 항상 3인칭의 객관적 시점과 명시된 종결 어미만을 사용하십시오.
    """
    
    human_msg = f"""
    [시스템명]
    {system_name}

    [사내 작성 가이드 라인]
    {doc_style_guide}

    [기획된 아웃라인]
    {doc_outline}

    [원시 기술 데이터]
    {technical_source}
    """

    # qa 에이전트에서 반환된 경우(피드백)
    if qa_feedback:
        human_msg += f"""
        \n[수석 QA 엔지니어의 필수 수정 지시사항]
        이전 작성본이 아래 사유로 반려되었습니다. 지적 사항을 반드시 반영하여 작성하십시오.
        {qa_feedback}
        """
        
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return {
        "doc_draft": response.content,
        "review_verdict": None # QA 평가를 초기화해서 다시 평가하기 위한 준비
        }

# ==============================================
# 문서 편집장 에이전트
def compliance_editor_agent(state: TechDocState) -> dict:
    print("[Node: Compliance Editor] 기술 문서 포맷 및 1차 교정 중...")
    
    doc_draft = state.get("doc_draft")
    
    sys_msg = f"""
    # Role
    당신은 기술 문서의 가독성과 포맷 정합성을 교정하는 테크니컬 에디터(Peer Reviewer)입니다.

    # Instructions
    작성된 기술 문서 초안의 문맥 흐름을 매끄럽게 교정하고, 기술 용어의 일관성을 맞추십시오.

    # Steps
    1. 초안을 정독하며 어색한 번역투 문장이나 지나치게 긴 문장을 간결하게 분리하십시오.
    2. 불필요한 부사나 형용사를 제거하고 기술적인 건조한 톤으로 변경하십시오.
    3. 마크다운 포맷팅(볼드체, 코드 블록, 리스트)이 깨진 곳이 있다면 올바르게 복원하십시오.

    # Expectations
    최종 QA 시스템(Critic)을 무사히 통과할 수 있도록, 문법적 오류와 포맷 결함이 완벽히 제거된 깔끔한 문서를 만들어야 합니다.

    # Narrowing
    - 절대 글의 논리 구조(목차)나 기술적 팩트를 임의로 변경하지 마십시오.
    - 부가적인 코멘트나 설명 없이, 교정이 완료된 마크다운 텍스트 원문만 출력하십시오.
    """
    
    human_msg = f"""
    [교정 대상 초안]
    {doc_draft}
    """
    
    response = critic_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    raw_content = response.content
    if isinstance(raw_content, list):
        # clean_text = raw_content[0]['text']
        clean_text = "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item) for item in raw_content
        )
    else:
        clean_text =str(raw_content)
    
    return {"tech_reviewed_content": clean_text, 'review_verdict': None}