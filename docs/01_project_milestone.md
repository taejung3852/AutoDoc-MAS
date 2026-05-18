# AutoDoc-MAS

## 프로젝트 개요
비정형 기술 데이터(코드 스니펫, 회의록, 아키텍처 다이어그램 등)를 규격화된 기업용 기술 문서로 자동 변환하고 관리하는 LangGraph 기반 멀티 에이전트 시스템.
단일 LLM 호출의 한계인 맥락 단절(Context Loss)과 기술적 환각(Hallucination)을 다중 에이전트 간 Reflection 루프와 VectorDB 기반 Long-term Memory로 제어.

---

## 마일스톤

- [x] **Phase 0: 설계 및 아키텍처 확정**
  - 계층형 Supervisor 아키텍처 설계
  - 신규 문서 / 업데이트 문서 파이프라인을 독립된 서브 그래프로 분리하는 구조 확정
  - VectorDB 기반 Context Injection으로 이전 문서 맥락 유지 전략 설계
  - QA Critic 노드의 PASS / REVISE 판정 루프 및 HITL 개입 지점 설계

- [x] **Phase 1: 상태(State) 정의 및 더미 노드 구축**
  - `TechDocState` 스키마 작성 (TypedDict 기반)
  - 에이전트 연동 전 라우팅 검증용 더미 노드 생성

- [x] **Phase 2: LangGraph 기반 워크플로우 뼈대 조립 및 라우팅 테스트**
  - `graph.py`에서 메인/서브 그래프 노드 간 Edge 연결
  - 순환 루프, Conditional Edge 동작 검증 완료

- [x] **Phase 3: LLM 연동 및 RISEN 기반 프롬프트 체계 확립**
  - Google Gemini 연동 (`writer_llm`, `critic_llm` 역할 분리)
  - RISEN 프레임워크(Role-Instructions-Steps-Expectations-Narrowing) 기반 프롬프트 템플릿 문서화 (`docs/04_prompt_guide.md`)

- [x] **Phase 4: 서브 그래프 구축 및 멀티모달 연동**
  - 신규 문서 파이프라인 (`new_doc_graph`): Planner → Executor → Compliance Editor
  - 업데이트 문서 파이프라인 (`update_doc_graph`): Context Loader → Planner → Executor → QA Critic
  - 다이어그램 이미지(Base64) 분석 및 최적 배치 노드 구현 (`diagram_analysis`, `image_placement`)
  - 메인 그래프(`supervisor`)와 서브 그래프 계층형 라우팅 통합

- [x] **Phase 5: VectorDB 연동 및 Long-term Memory 구현**
  - ChromaDB 기반 시스템 네임스페이스별 문서 컨텍스트 저장 로직 구현
  - 발행 시 핵심 아키텍처 메타데이터만 압축 추출하여 저장하는 전략 적용
  - RAG 기반 맥락 주입(Context Injection) 및 연속성 검증 완료

- [x] **Phase 6: HITL 및 Reflection 루프 완성**
  - QA Critic 에이전트의 PASS / REVISE 판정 기반 자가 수정 루프 구현
  - `max_revisions` 초과 시 강제 HITL 전환 로직 추가
  - LangGraph Checkpointer 기반 Interrupt 및 재개 파이프라인 연동
  - Streamlit 마크다운 에디터 + 실시간 렌더링 뷰어 HITL UI 구현

- [ ] **Phase 7: 정량 검증 및 성과 측정**
  - SQLite 기반 파이프라인 실행 로그 수집 (revision_count, verdict, 처리 시간)
  - 단일 LLM 대비 가이드라인 준수율 비교 테스트
  - README 정량적 성과 지표 섹션 업데이트

- [ ] **Phase 8: 데이터 수집 서브 그래프 (Data Ingest Graph) 통합**
  - PDF 입력 지원: Upstage Document Parser 연동 (다단 레이아웃, 테이블 구조 보존)
  - `input_router` 노드로 파일 타입별 파싱 분기 (`.pdf` / `.txt` / `.md`)
  - 파싱 결과 정제 및 검증 게이트 구현