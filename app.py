import streamlit as st
import tempfile
import os
import re
import uuid
from src.graphs.main_graph import app as doc_workflow
from src.memory import get_all_systems, delete_system, save_user_guideline
from src.utils import synthesize_tech_feedback


st.set_page_config(page_title="AutoDoc-MAS", layout="wide")


# ==========================================
# ⚙️ 모달(Pop-up) 창: 시스템 전역 설정
# ==========================================
@st.dialog("⚙️ 품질 보증(QA) 및 규격 설정")
def show_settings():
    st.markdown("모든 시스템 문서화 파이프라인에 공통으로 적용될 규격을 설정합니다.")

    default_guide = """1. 시점 및 어조: 반드시 3인칭 객관적 시점을 유지하고, 감정적인 표현을 배제하십시오. 종결 어미는 '~합니다', '~입니다'로 통일하십시오.
2. 구조 및 레이아웃: 문단은 최대 3문장을 넘지 않게 짧게 쓰고, 나열할 내용은 반드시 불릿 포인트(-)를 사용하십시오.
3. 코드 및 데이터 명세: 모든 코드 스니펫에는 반드시 언어 태그(e.g., ```json)를 달고, 주요 Endpoint나 설정값은 볼드체(**)로 강조하십시오.
4. 명확성: 두루뭉술한 표현을 피하고, 원시 데이터에 존재하는 정확한 수치와 팩트만을 서술하십시오."""

    doc_style_guide_input = st.text_area(
        "사내 기술 문서 작성 가이드라인",
        value=st.session_state.get('doc_style_guide', default_guide),
        height=150
    )

    max_revisions = st.slider(
        "QA 시스템 최대 반려(재작성) 허용 횟수",
        min_value=1, max_value=3,
        value=st.session_state.get('max_revisions', 2)
    )

    if st.button("설정 저장", use_container_width=True):
        st.session_state['doc_style_guide'] = doc_style_guide_input
        st.session_state['max_revisions'] = max_revisions
        st.rerun()
        
@st.dialog("⚠️ 입력 오류")
def show_input_error(message: str):
    st.warning(message)
    if st.button("확인", use_container_width=True):
        st.rerun()
        

# ==========================================
# 세션 초기화
# ==========================================
if 'input_key' not in st.session_state:
    st.session_state['input_key'] = 0  # ← 추가
if 'doc_style_guide' not in st.session_state:
    st.session_state['doc_style_guide'] = """1. 3인칭 객관적 시점 및 '~합니다' 형태의 기술적 어조 사용.
2. 마크다운 계층 구조(#, ##, ###) 엄수.
3. 코드 스니펫 작성 시 언어 태그(e.g., ```json) 필수 적용."""
if 'max_revisions' not in st.session_state:
    st.session_state['max_revisions'] = 2


# ==========================================
# 👈 사이드바: 룸(시스템) 네비게이션
# ==========================================
with st.sidebar:
    st.title("AutoDoc-MAS 📚")
    st.markdown("엔터프라이즈 기술 문서 통제실")

    if st.button("➕ 새로운 시스템 시작", use_container_width=True, type="primary"):
        st.session_state['selected_system'] = "NEW"
        st.session_state['input_key'] += 1
        if 'thread_id' in st.session_state:
            del st.session_state['thread_id']
        st.rerun()

    st.markdown("---")
    st.subheader("저장된 시스템 목록")

    existing_systems = get_all_systems()
    for sys in existing_systems:
        col1, col2 = st.columns([8, 2])
        with col1:
            if st.button(f"📁 {sys}", key=f"btn_{sys}", use_container_width=True):
                st.session_state['selected_system'] = sys
                st.session_state['is_update_request'] = True
                st.session_state['input_key'] += 1
                if 'thread_id' in st.session_state:
                    del st.session_state['thread_id']
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{sys}"):
                delete_system(sys)
                st.rerun()


# ==========================================
# 🖥️ 메인 화면 및 헤더
# ==========================================
col_header1, col_header2 = st.columns([8, 2])
with col_header1:
    st.header(
        st.session_state.get('selected_system', '새로운 시스템')
        if st.session_state.get('selected_system') != "NEW"
        else "✨ 새로운 기술 문서 파이프라인 생성"
    )
with col_header2:
    if st.button("⚙️ QA 규격 설정"):
        show_settings()

st.markdown("---")

current_system = st.session_state.get('selected_system', "NEW")


# ==========================================
# 파이프라인 입력 및 실행 폼
# ==========================================
if current_system == "NEW":
    system_name = st.text_input("시스템 식별자 (네임스페이스)", placeholder="예: Payment-Gateway-v1")
    is_update_request = False
else:
    system_name = current_system
    is_update_request = True
    st.info("이전에 저장된 시스템 맥락(VectorDB)을 바탕으로 업데이트 파이프라인(RAG)이 가동됩니다.")

doc_type = st.selectbox(
    "산출물 유형",
    ["기능 명세서 (Feature Spec)", "릴리즈 노트 (Release Note)", "API 연동 문서 (API Doc)"]
)

col_input1, col_input2 = st.columns(2)
with col_input1:
    technical_source = st.text_area(
        "파편화된 원시 기술 데이터 입력 (회의록, 로그, 슬랙 등)",
        height=250,
        key=f"technical_source_{st.session_state['input_key']}"
    )
    uploaded_pdf = st.file_uploader(
        "또는 PDF 파일 업로드 (선택)",
        type=['pdf'],
        accept_multiple_files=False,
        key=f"uploaded_pdf_{st.session_state['input_key']}"
    )

with col_input2:
    uploaded_diagrams = st.file_uploader(
        "다이어그램 / 아키텍처 이미지 (선택)",
        type=['png', 'jpg'],
        accept_multiple_files=True,
        key=f"uploaded_diagrams_{st.session_state['input_key']}"
    )


if st.button("🚀 AutoDoc-MAS 파이프라인 가동", use_container_width=True, type="primary"):
    parse_failed = False
    # 검증: 텍스트도 없고 PDF도 없으면 에러

    if technical_source and uploaded_pdf:
        show_input_error("텍스트 입력과 PDF 업로드는 동시에 사용할 수 없습니다. 하나만 선택해주세요.")
        st.stop()

    
    if not system_name or (not technical_source and not uploaded_pdf):
        st.error("시스템 식별자와 기술 데이터(텍스트 또는 PDF)는 필수입니다.")
        st.stop()

    st.session_state['system_name'] = system_name

    # 다이어그램 임시 저장
    temp_diagram_paths = []
    if uploaded_diagrams:
        temp_dir = tempfile.mkdtemp()
        for img in uploaded_diagrams:
            temp_path = os.path.join(temp_dir, img.name)
            with open(temp_path, "wb") as f:
                f.write(img.getbuffer())
            temp_diagram_paths.append(temp_path)

    # PDF 임시 저장
    raw_file_path = None
    file_type = "text"

    if uploaded_pdf:
        temp_dir = tempfile.mkdtemp()
        raw_file_path = os.path.join(temp_dir, uploaded_pdf.name)
        with open(raw_file_path, "wb") as f:
            f.write(uploaded_pdf.getbuffer())
        file_type = "pdf"

    st.session_state['thread_id'] = str(uuid.uuid4())
    config = {"configurable": {"thread_id": st.session_state['thread_id']}}

    initial_state = {
        "doc_type": "feature_spec",
        "system_name": system_name,
        "doc_style_guide": st.session_state['doc_style_guide'],
        "technical_source": technical_source if technical_source else None,
        "is_update_request": is_update_request,
        "revision_count": 0,
        "max_revisions": st.session_state['max_revisions'],
        "captured_diagrams": temp_diagram_paths,
        "raw_file_path": raw_file_path,
        "file_type": file_type,
    }

    with st.status("에이전트 작업 진행 중...", expanded=True) as status:
        for output in doc_workflow.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, state_update in output.items():
                st.write(f"✅ 노드 통과: [{node_name}]")

        snapshot = doc_workflow.get_state(config)
        parse_failed = snapshot.values.get("parser_verdict") == "FAIL"

        if parse_failed:
            status.update(label="❌ 파일 파싱 실패", state="error", expanded=True)
        else:
            status.update(label="파이프라인 일시 정지 (사용자 검토 대기)", state="complete", expanded=False)

    # with 블록 밖에서 stop 호출
    if parse_failed:
        st.error("PDF가 손상되었거나 인코딩 문제가 있을 수 있습니다.")
        st.stop()


# ==========================================
# HITL (수동 검토) 및 결과 뷰어
# ==========================================
if 'thread_id' in st.session_state:
    config = {"configurable": {"thread_id": st.session_state['thread_id']}}
    current_snapshot = doc_workflow.get_state(config)
    full_state = current_snapshot.values

    is_paused = len(current_snapshot.next) > 0 and current_snapshot.next[0] == "human_approval"

    if is_paused:
        st.markdown("---")
        st.error("👀 검토 필요: QA 검증이 완료되었거나 최대 수정 횟수에 도달했습니다. 내용을 수정하고 승인해 주세요.")

        draft_text = full_state.get("tech_reviewed_content", "")

        view_col, edit_col = st.columns(2)

        with edit_col:
            st.markdown("### ✍️ 마크다운 에디터 (수정용)")
            st.info("에디터 바깥을 클릭하거나 Ctrl+Enter를 누르면 좌측 미리보기가 갱신됩니다.")
            edited_text = st.text_area(
                "이곳에서 원시 마크다운을 직접 수정하세요.",
                value=draft_text,
                height=600,
                label_visibility="collapsed"
            )

        with view_col:
            st.markdown("### 👁️ 실시간 미리보기")
            st.markdown(edited_text)

        st.markdown("---")
        c1, c2 = st.columns(2)

        with c1:
            fb_tech = st.text_input(
                "기술적 팩트 지적 (가이드라인화 됨)",
                help="[역할] 해당 시스템에서 AI가 절대 틀려서는 안 되는 도메인 지식\n\n[예시] '결제 상태값은 반드시 대문자(PENDING, SUCCESS)로만 표기해라', '레거시 DB인 old_orders는 절대 언급하지 마라'"
            )

        with c2:
            fb_comp = st.text_input(
                "포맷 지적 (가이드라인화 됨)",
                help="[역할] 문서의 레이아웃과 스타일 규격 강제\n\n[예시] 'API 파라미터 설명은 불릿 포인트 대신 무조건 마크다운 표(Table)를 사용해라'"
            )

        if st.button("문서 최종 승인 및 시스템 병합", type="primary", use_container_width=True):
            with st.spinner("피드백 분석 및 규칙 추출 중..."):
                if fb_tech or fb_comp or (draft_text != edited_text):
                    synthesized = synthesize_tech_feedback(edited_text, fb_tech, fb_comp)

                    tech_rule = synthesized.get('technical_rule', "")
                    comp_rule = synthesized.get('compliance_rule', "")

                    if tech_rule or comp_rule:
                        combined_guideline = f"[도메인 기술 지침]: {tech_rule}\n[포맷 및 규격 지침]: {comp_rule}"
                        save_user_guideline(full_state['system_name'], combined_guideline)

            doc_workflow.update_state(
                config,
                {"human_review_complete": True, "final_doc": edited_text}
            )

            with st.spinner("최종 산출물 저장 및 VectorDB 동기화 중..."):
                for _ in doc_workflow.stream(None, config=config): pass
            st.success("✅ 시스템 형상 등록 완료!")
            st.rerun()

    else:
        st.markdown("---")
        st.markdown(f"### 🏆 최종 기술 문서 산출물 [{full_state.get('system_name', '')}]")

        final_artifact = full_state.get("final_doc") or full_state.get("tech_reviewed_content")

        if final_artifact:
            view_tab, code_tab = st.tabs(["📄 렌더링 뷰어", "💻 마크다운 소스"])
            with view_tab:
                display_text = re.sub(
                    r'!\[([^\]]*)\]\([^\)]*\)',
                    r'\n\n> 🖼️ **[다이어그램 삽입 위치: \1]**\n\n',
                    final_artifact, flags=re.IGNORECASE
                )
                st.markdown(display_text)
            with code_tab:
                st.code(final_artifact, language="markdown")