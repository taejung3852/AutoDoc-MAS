from src.state import TechDocState
from langchain_core.messages import SystemMessage, HumanMessage
from src.utils import writer_llm, critic_llm

# ==============================================
# Supervisor 에이전트
def update_doc_supervisor_agent(state: TechDocState) -> dict:
    print("\n[Node: Continuation Supervisor] 연재글 작성 부서 내부 작업 지시 중...")

    if not state.get("technical_source"):
        print("  -> ⚠️ 경고: 기술 자료(Source)가 없습니다. 메인으로 복귀합니다.")
        return {"sub_next_step": "end"}

    if not state.get("doc_outline"):
        next_step = "structure_planning"
    elif not state.get("doc_draft"):
        next_step = "technical_drafting"
    elif not state.get("tech_reviewed_content"):
        next_step = "compliance_editor"
    else:
        print("  -> 업데이트 서브 그래프 작업 완료! 메인 Supervisor로 복귀합니다.")
        return {'sub_next_step':'end'}
        
    return {"sub_next_step": next_step}

# ==============================================
# 아웃라인 작성 에이전트
def update_structure_planning_agent(state: TechDocState) -> dict:
    print("[Node: Update Structure Planning] 시스템 업데이트를 반영한 아웃라인 재설계 중...")    

    system_name = state.get('system_name')
    previous_doc_context = state.get('previous_doc_context')
    technical_source = state.get('technical_source')
    
    # 연재글 전용 프롬프트: 이전 맥락과의 연결성에 집중
    sys_msg = f"""
    # Role
    당신은 기존 시스템 아키텍처 문서를 유지보수하는 수석 테크니컬 기획자(Technical Planner)입니다.

    # Instructions
    기존 시스템의 아키텍처 맥락(Previous Context)을 훼손하지 않으면서, 신규 변경 사항(Technical Source)이 자연스럽게 반영된 기술 문서의 목차(Outline)를 재설계하십시오.

    # Steps
    1. '이전 문서 맥락'을 분석하여 현재 시스템의 기본 뼈대를 파악하십시오.
    2. '신규 기술 데이터'를 분석하여 추가, 변경, 또는 삭제되어야 할 컴포넌트를 식별하십시오.
    3. 기존의 큰 목차 흐름을 최대한 유지하되, 변경 사항이 반영될 적절한 위치(서브 목차 등)를 잡아 뼈대를 구성하십시오.
    4. 각 목차가 어떤 내용을 담을지 1줄 요약으로 명시하십시오.

    # Expectations
    개발자가 이 목차를 통해 '기존 시스템이 어떻게 생겼고, 이번에 무엇이 바뀌었는지' 직관적으로 파악할 수 있어야 합니다.

    # Narrowing
    - 기존 맥락에 없는 완전히 새로운 시스템을 창조하지 마십시오.
    - 오직 마크다운 헤딩(#, ##)과 Bullet Point만 사용하십시오.
    """
    
    human_msg = f"""
    [문서화 대상 시스템명]
    {system_name}
    
    [이전 문서의 핵심 맥락 (VectorDB)]
    {previous_doc_context}

    [반영해야 할 신규 기술 데이터]
    {technical_source}
    """
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return {"doc_outline": response.content}

# ==============================================
# 초안작성 에이전트
def update_technical_drafting_agent(state: TechDocState) -> dict:
    print("[Node: Update Technical Drafting] 변경 사항이 반영된 기술 초안 작성 중...")
    qa_feedback = state.get('qa_feedback')
    system_name = state.get('system_name')
    doc_style_guide = state.get('doc_style_guide')
    previous_doc_context = state.get('previous_doc_context')
    doc_outline = state.get('doc_outline')
    technical_source = state.get('technical_source')
    
    # 이전 맥락을 자연스럽게 잇는 기술 초안 작성
    sys_msg = """
    # Role
    당신은 변경된 시스템 명세서를 정확하고 객관적으로 업데이트하는 시니어 테크니컬 라이터입니다.

    # Instructions
    이전 시스템 맥락을 기반으로 기획된 아웃라인과 신규 기술 데이터를 결합하여, 업데이트된 기술 문서 초안을 작성하십시오.

    # Steps
    1. 아웃라인의 구조를 100% 준수하여 마크다운 헤딩을 전개하십시오.
    2. '이전 문서 맥락'에 있는 기본 개념은 장황하게 다시 설명하지 말고, 요약식으로 서술하거나 생략하여 가독성을 높이십시오.
    3. '신규 기술 데이터'를 바탕으로 변경된 API나 아키텍처의 상세 내용을 본문에 집중적으로 서술하십시오.
    4. 사내 작성 가이드라인의 포맷 규칙을 적용하여 문장을 다듬으십시오.

    # Expectations
    다른 부서의 엔지니어가 이 문서를 읽었을 때, 시스템의 과거와 현재 변경점이 명확하게(Clear) 구분되고, 기술적 오해가 없도록 작성되어야 합니다.

    # Narrowing
    - 항상 3인칭의 객관적인 시점으로 서술하십시오. (1인칭 표현 절대 금지)
    - 절대 원시 데이터나 이전 맥락에 없는 기술적 사실을 임의로 추가하지 마십시오.
    """
    
    human_msg = f"""
    [시스템명]
    {system_name}

    [사내 작성 가이드라인]
    {doc_style_guide}

    [이전 문서의 핵심 맥락]
    {previous_doc_context}

    [업데이트된 아웃라인]
    {doc_outline}

    [반영해야 할 신규 기술 데이터]
    {technical_source}
    """
    
    if qa_feedback:
        human_msg += f"""
        \n
        [수석 QA 엔지니어의 필수 수정 지시사항]
        이전 작성본이 아래와 같은 사유로 반려되었습니다. 지적 사항을 반드시 반영하여 작성하십시오.
        {qa_feedback}
        """
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return {"doc_draft": response.content, "review_verdict": None}

# ==============================================
# 문서 편집장 에이전트
def update_compliance_editor_agent(state: TechDocState) -> dict:
    print("[Node: Update Compliance Editor] 업데이트 문서 포맷 및 정합성 교정 중...")
    doc_draft = state.get("doc_draft")
    
    # 1편 에디터와 다르게 '이전 맥락'과의 연결성을 강조합니다.
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
        clean_text = "\n".join(
            item.get('text', '') if isinstance(item, dict) else str(item) for item in raw_content
        )    
    return {"tech_reviewed_content": clean_text, 'review_verdict': None}
