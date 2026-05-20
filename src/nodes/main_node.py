from langchain_core.messages import SystemMessage, HumanMessage
from src.utils import writer_llm, critic_llm
from src.state import TechDocState

from src.memory import save_doc_context
from src.utils import load_technical_source


# ==============================================
# Supervisor 에이전트
def supervisor_agent(state: TechDocState) -> dict:
    print("\n[Node: supervisor] 라우팅 판단 중...")

    is_update = state.get('is_update_request', False)
    reviewed_content = state.get("tech_reviewed_content")  
    verdict = state.get("review_verdict")
    rev_count = state.get("revision_count", 0)
    max_rev = state.get("max_revisions", 2)
    technical_source = state.get('technical_source')
    parser_verdict = state.get('parser_verdict')
    
    # 0. 전처리 필요 여부 판단 (최우선)
    #    - technical_source가 없고 raw_file_path가 있으면 → data_ingest_graph
    #    - parser_verdict가 FAIL이면 → 파이프라인 중단
    if parser_verdict == "FAIL":
        print("  -> 데이터 전처리 및 품질 검증 실패. 파이프라인을 중단합니다.")
        return {'next_step':None}
    
    if not parser_verdict:
        print("  -> 원본 파일 감지. 데이터 전처리 서브 그래프(data_ingest_graph)로 라우팅합니다.")
        return {'next_step': 'data_ingest_graph'}
         
    if not technical_source:
        print("  -> 에러: technical_source가 비어 있습니다. 파이프라인을 중단합니다.")
        return {"next_step": None}

    # 2. QA에서 반려(REVISE)된 상태인 경우 먼저 체크!
    elif verdict == "REVISE":
        if rev_count < max_rev:
            print(f"  -> QA 에이전트 반려됨. 재작성 요청 (현재 수정 횟수: {rev_count}/{max_rev})")
            next_step = "update_doc_graph" if is_update else "new_doc_graph"
        else:
            print(f"  -> 최대 수정 횟수({max_rev}회) 도달. 강제로 휴먼 리뷰로 넘깁니다.")
            next_step = 'human_approval'

    # 3. 에디터가 작성한 기술 초안이 없는 경우 (최초 작성 시)
    elif not reviewed_content:
        next_step = "update_doc_graph" if is_update else "new_doc_graph"

    # 4. 작성은 되어있지만 QA 판정(Verdict)을 아직 안 받은 경우
    elif not verdict:
        next_step = "qa_critic"

    # 5. QA를 통과(PASS)한 경우
    elif verdict == "PASS":
        if not state.get('human_review_complete'):
            next_step = 'human_approval'

        # HITL도 끝났다면 마무리단게로
        else:
            next_step = "final_publish"

    print(f"  -> 다음 단계: {next_step}")
    return {"next_step": next_step}



# ==============================================
# QA 에이전트
def qa_critic_agent(state: TechDocState) -> dict:
    print("[Node: QA Critic] 품질 보증 시스템이 문서의 규격과 정합성을 검증합니다...")
    reviewed_content = state.get('tech_reviewed_content')
    style_guide = state.get('doc_style_guide')
    current_count = state.get('revision_count', 0)
    max_revisions = state.get('max_revisions', 2)

    sys_msg = f"""
    # Role
    당신은 사실 관계(Fact-Checking)의 무결성을 최우선으로 검증하는 수석 QA 엔지니어입니다.

    # Instructions
    초안 문서가 '원본 기술 데이터'를 100% 왜곡 없이 담아냈는지 검증하고, '사내 작성 가이드라인' 준수율을 평가하여 최종 합격(PASS) 또는 반려(REVISE)를 결정하십시오.

    # Steps
    1. [팩트 검증 - 무관용 원칙]: 원본 기술 데이터와 초안을 한 줄씩 대조하십시오. 원본에 없는 시스템 목적, 기대 효과, 향후 고려사항, 예외 처리 로직 등을 AI가 임의로 창작(Hallucination)한 문장이 단 한 개라도 있다면 즉시 반려(REVISE) 사유로 기록하십시오.
    2. [규격 검증 - 실용적 허용]: 사내 작성 가이드라인(3인칭 어조, 불릿 포인트, 언어 태그 등)이 80% 이상 지켜졌는지 확인하십시오.
    3. [최종 판정]: 팩트 왜곡 및 창작이 발견되면 무조건 반려(REVISE)하십시오. 단, 팩트 창작이 없고 내용이 정확하다면, 1~2개의 사소한 포맷팅 실수나 마크다운 누락은 너그럽게 통과(PASS)시키십시오.

    # Expectations
    당신의 핵심 목표는 개발자가 하지도 않은 말을 그럴듯하게 적어놓은 '소설(Hallucination)'을 완벽하게 차단하는 것입니다. 사소한 띄어쓰기 검사가 아님을 명심하십시오.

    # Narrowing
    - 절대 사소한 포맷팅 실수나 띄어쓰기를 이유로 문서를 반려하지 마십시오. 반려는 오직 '팩트 창작'이나 '가이드라인 전면 위반'일 때만 수행하십시오.
    - 피드백은 다음 에이전트가 직관적으로 고칠 수 있도록 3문장 이내의 명확한 리스트 형태로만 작성하십시오.
    - 응답의 맨 마지막 줄에는 반드시 `VERDICT: PASS` 또는 `VERDICT: REVISE` 중 하나를 정확히 출력하십시오.
    """

    human_msg = f"""
    [사내 가이드라인]
    {style_guide}
    
    [검증할 기술 문서 초안]
    검토할 글: {reviewed_content}
    """
    
    response = critic_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])

    raw_content = response.content
    if isinstance(raw_content, list):
        feedback = "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item) 
            for item in raw_content
        )
    else:
        feedback = str(raw_content)
    print(f"  -> QA 리포트 생성 완료 (판정 결과 대기 중)\n")

    if "VERDICT: PASS" in feedback.upper():
        print("  -> ✅ 규격 통과 (PASS)")
        return {
            "final_doc": reviewed_content, 
            "review_verdict": "PASS",
            'qa_feedback': None,
            "messages": [response]
        }
    else:
        print(f"  -> ❌ 규격 미달 (REVISE)")
        if current_count + 1 >= max_revisions:
            print("  -> ⚠️ 최대 수정 횟수 도달. 현재 버전을 유지하고 사용자 검토로 넘깁니다.")
            return {
                "revision_count": current_count + 1, 
                "review_verdict": "REVISE",
                "qa_feedback": feedback,
                "messages": [response]
                # tech_reviewed_content 등은 덮어쓰지 않고 기존 상태 유지
            }
        else:
            # 아직 재작성 기회가 남았다면 기존안을 파기하고 다시 쓰도록 유도
            return {
                "revision_count": current_count + 1, 
                "review_verdict": "REVISE",
                "doc_draft": None,
                "tech_reviewed_content": None, 
                "qa_feedback": feedback,
                "messages": [response]
            }
# ==============================================
# HITL 에이전트
def human_approval_agent(state: TechDocState) -> dict:
    print("\n[Node: Human Approval] 에이전트 작업 완료. 사용자의 최종 기술 검토(HITL)를 대기합니다...")
    return {}

# ==============================================
# 최종 마무리 에이전트
def final_publish_agent(state: TechDocState) -> dict:
    print("\n[Node: Final Publish] 최종 문서 승인 완료. 시스템 형상 관리(VectorDB)에 기록합니다...")
    final_doc = state.get("final_doc")
    system_name = state.get('system_name')

    
    # 문서 전체가 아닌 아키텍처/기술 요약 메타데이터만 추출해서 DB에 저장
    sys_msg = f"""
    # Role
    당신은 시스템 아키텍처 데이터베이스를 관리하는 수석 데이터 아키텍트입니다.

    # Instructions
    완성된 기술 문서에서 장기 기억(VectorDB)에 저장할 핵심 아키텍처 메타데이터만 정확하게 추출하십시오.

    # Steps
    1. 문서 내에서 시스템의 핵심 목적, 주요 컴포넌트, 그리고 데이터 흐름을 식별하십시오.
    2. 변경된 아키텍처나 API 명세의 핵심 키워드를 추출하십시오.
    3. 불필요한 서술어를 모두 제거하고 명사/개념 위주의 요약본을 작성하십시오.

    # Expectations
    이 요약본은 향후 다른 에이전트가 시스템 업데이트 문서를 작성할 때 '과거 아키텍처 맥락'으로 활용될 핵심 설계 지식입니다.

    # Narrowing
    - 절대 원본 글을 그대로 복사하거나 감성적인 문장을 포함하지 마십시오.
    - 반드시 아래의 Format을 반드시 지켜서 작성하십시오.
    
    [Format]
    [시스템 핵심 목적]
    - (1줄 요약)
    [주요 아키텍처 및 컴포넌트]
    - (컴포넌트 1: 역할)
    - (컴포넌트 2: 역할)
    """

    human_msg = f"""
    [승인된 기술 문서 원본]
    {final_doc}
    """
    
    summary_response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    
    raw_summary = summary_response.content
    if isinstance(raw_summary, list):
        summary_text = "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item) 
            for item in raw_summary
        )
    else:
        summary_text = str(raw_summary)
    print("  -> 📝 아키텍처 메타데이터 추출 완료. DB 갱신을 진행합니다.")
    
    save_doc_context(system_name, summary_text)
    
    print("\n====================================")
    print(f"✅ [{system_name}] 기술 문서 파이프라인이 성공적으로 종료되었습니다.")
    print("====================================")
    
    return {}