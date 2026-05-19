# from pydantic import BaseModel
from typing import Annotated, Optional, Literal, TypedDict
from langgraph.graph import add_messages

class TechDocState(TypedDict):
    messages: Annotated[list, add_messages] # LLM 답변 저장할 필드

    # 필수 초기 설정값
    doc_type: Literal['feature_spec', 'release_note', 'api_doc'] # 명확한 문서 타입 지정
    system_name: str                        # 문서화할 시스템 이름
    doc_style_guide: str                    # 사내 기술 문서 작성 가이드라인
    technical_source: Optional[str]         # 개발자 메모, 소스코드, 회의록 등 입력 데이터
    is_update_request: bool                 # 기존 분서 업데이트 여부
    raw_file_path: Optional[str]            # PDF 등 원본 파일 경로
    file_type: Optional[str]                # "pdf" or "text"

    # 상태 업데이투 과정에서 채워지는 필드들 (반드시 None으로 기본값 지정)
    previous_doc_context: str               # 버전 업데이트 시 참고할 이전 문서의 맥락/용어집
    next_step: Optional[Literal[            # supervisor가 판단한 경로 선택 목록
        'data_ingest_graph',
        'new_doc_graph', 
        'update_doc_graph', 
        'qa_critic',                        # 품질 보증 단계
        'human_approval', 
        'final_publish'
        ]]
    sub_next_step: Optional[Literal[        # 하위 그래프들의 경로 선택 목록
        'structure_planning',               # 목차 기획
        'context_injection'
        'diagram_analysis',                 # 아키텍처 다이어그램 분석
        'technical_drafting',               # 기술 초안 작성
        'compliance_editor',                # 사내 가이드라인 준수 여부 교정
        'end'
        ]]    
    data_ingest_next_step: Optional[Literal[# 데이터 처리를 위한 서브 그래프 경로 선택 목록
        'pdf_parser',                       # PDF 형식으로 들어올 떄 전처리 에이전트
        'text_cleaner',                     # 텍스트 형식으로 들어올 때 전처리 에이전트
        'parse_validator',                  # 전처리 결과 검증
        'end'
        ]]

    # 문서 상태 (Outputs & QA)
    doc_outline: Optional[str]              # 기획 단계의 문서 목차
    doc_draft: Optional[str]                # 기술 문서 초안
    tech_reviewed_content: Optional[str]    # 기술 교정 완성본
    final_doc: Optional[str]                # 최종 승인된 기술 문서

    # 검증 및 피드백
    review_verdict: Optional[Literal['PASS', 'REVISE', 'REJECT']]
    qa_feedback: Optional[str]              # 규격 위반 사항에 대한 구체적 리포트
    revision_count: int                     
    max_revisions: int                      # 최대 거절 횟수

    ## ingest 검증 결과
    parser_verdict: Optional[Literal['PASS', 'FAIL']]              # 데이터 검증 실패 메시지

    # HITL
    human_review_complete: Optional[bool]    # 사용자 검토 완료 여부
    human_feedback_technical: Optional[str]  # 기술적 팩트 수정 지시
    human_feedback_compliance: Optional[str] # 포맷/구조 수정 지시

    captured_diagrams: Optional[list[str]]