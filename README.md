# AutoDoc-MAS

![Main Workflow Diagram](./AutoDoc-MAS_workflow.png)
<!-- 이미지 첨부: 프로젝트 로고 또는 시스템의 전체 목적을 보여주는 심플한 아키텍처 개요 이미지 -->
AutoDoc-MAS는 개발 과정에서 발생하는 비정형 기술 데이터(코드 스니펫, 회의록, 아키텍처 다이어그램 등)를 규격화된 기업용 기술 문서로 변환하고 관리하는 LangGraph 기반 멀티 에이전트 시스템(MAS)입니다.

단일 LLM 호출에 의존하지 않고, 이전 문서의 맥락 인지와 사내 가이드라인 준수 여부를 다중 에이전트 간의 상호 검증(Reflection) 루프를 통해 제어함으로써 기술 문서의 논리적 정합성을 확보합니다.
<!--[이미지/GIF 첨부: Streamlit UI에서 원시 데이터가 규격화된 문서로 자동 변환되는 과정을 담은 짧은 시연 화면]-->
---

## 프로젝트 배경 및 동기

**문제 정의**

소프트웨어 아키텍처와 코드는 지속적으로 변경되지만, 이를 반영한 기술 문서화 작업은 유지보수 비용 문제로 인해 동기화가 지연되는 경우가 많습니다. 기존의 단일 LLM이나 단순 검색 증강 생성(RAG) 기법을 도입할 경우, 시스템 규모가 커질수록 기존 문서와의 맥락 단절(Context Loss)이나 기술적 환각(Hallucination) 현상이 발생하여 실무 적용에 한계가 존재합니다.

**해결 방안**

본 프로젝트는 문서화 워크플로우를 기획(Planner), 작성(Executor), 검증(Critic) 역할로 분리한 멀티 에이전트 아키텍처를 채택했습니다. 시스템 내부에 독립적인 피드백 루프를 구축하여 사내 기술 표준을 강제하고, 사람의 개입을 최소화한 상태에서 신뢰도 높은 기술 문서를 자동 갱신할 수 있는 파이프라인을 설계했습니다.
<!--[이미지 첨부: 파편화된 메모/코드 -> AutoDoc-MAS -> 정돈된 기술 문서로 이어지는 데이터 흐름 인포그래픽]-->

---

## 시스템 아키텍처

메인 Supervisor를 중심으로 한 계층형 멀티 에이전트 구조를 채택하여 복잡한 문서화 공정을 자동화합니다.
<!--[이미지 첨부: src/graph.py에 정의된 전체 노드 라우팅 시퀀스 다이어그램]-->

### 1. New Doc Graph (신규 문서 파이프라인)
새로운 시스템이나 마이크로서비스에 대한 최초 기술 문서 작성을 담당합니다.
- **Planner (`structure_planning`):** 입력된 기술 소스를 분석하여 문서의 아웃라인 구조를 설계합니다.
- **Executor (`technical_drafting`, `diagram_analysis`):** 아웃라인에 기반하여 초안을 작성하고, 비전 데이터를 분석해 최적의 위치에 이미지를 배치합니다.
- **Critic (`compliance_editor`):** 사내 표준 규격 준수 여부와 기술적 오류를 검토 및 윤문합니다.
<!--[이미지 첨부: 신규 문서 전용 서브 그래프 다이어그램 (Planner-Executor-Critic 구조)]-->
![Intro Workflow Diagram](./new_doc_workflow.png)

### 2. Update Doc Graph (업데이트 문서 파이프라인)
기존 문서의 맥락을 유지하며 시스템 변경 사항을 반영하는 파이프라인입니다.
- **Context Loader (`context_injection`):** VectorDB에서 이전 문서의 핵심 용어와 결론을 로드하여 맥락을 주입합니다.
- **Planner (`update_structure_planning`):** 주입된 맥락과 신규 변경 사항을 결합하여 업데이트된 아웃라인을 기획합니다.
- **Executor (`update_technical_drafting`, `update_diagram_analysis`):** 이전 서사를 유지하며 변경된 기술 내용을 본문에 반영합니다.
- **Critic (`update_qa_critic`):** 기존 문서와의 용어 통일성 및 업데이트 내용의 정합성을 최종 검증합니다.
<!--[이미지 첨부: 기존 문서 맥락이 신규 데이터와 결합되는 RAG 과정이 포함된 서브 그래프 다이어그램]-->
![Continuation Workflow Diagram](./update_doc_workflow.png)

---

## 핵심 기술 및 엔지니어링 포인트

### 1. LangGraph 기반 오케스트레이션
순차적인 체인 구조의 한계를 넘어, StateGraph 위에서 에이전트들이 협업하는 순환형 구조를 설계했습니다.
- **Supervisor Agent:** 전체 워크플로우의 상태(TechDocState)를 평가하고 조건부 엣지(Conditional Edges)를 통해 최적의 노드로 동적 라우팅을 수행합니다.

### 2. Long-term Memory 관리 전략
ChromaDB를 연동하여 프로젝트 단위의 **문서 네임스페이스**를 구축했습니다.
- **맥락 인지 (Context-Aware):** 과거 버전에 기록된 기술 개념과 결론을 VectorDB에서 검색 및 주입하여, 중복 서술을 방지하고 시스템 히스토리를 유지합니다.
- **메타데이터 압축:** 문서 발행 시 전체 텍스트가 아닌 핵심 키워드와 가이드라인 준수 사항만 메타데이터로 요약 저장하여 검색 효율을 높입니다.
<!--[이미지 첨부: 문서 발행 시 핵심 메타데이터가 VectorDB에 저장되고, 다음 업데이트 시 검색 및 주입(Injection)되는 과정]-->

### 3. Reflection
- Critic 에이전트의 검증을 통과하지 못할 경우(REVISE), 피드백 내용을 Executor 에이전트에게 반환합니다. 무한 루프 방지를 위해 최대 수정 횟수 제한(max_revisions)을 두어 파이프라인의 안정성을 보장합니다.
<!--[이미지 첨부: QA Critic 에이전트가 사내 가이드라인 위반을 발견하고 REVISE 판정을 내리는 터미널 로그 또는 UI 캡처 화면]-->

### 4. Human-in-the-loop (HITL) 제어
- 최종 문서 발행 전, 시스템이 대기 상태(Interrupt)로 전환되어 사용자가 직접 검토하고 수정안을 상태에 반영할 수 있는 인터페이스를 제공합니다.

---

<!-- ## 정량적 성과 지표
> ⚠️ **[TODO / 작성 예정]** 시스템 구축 및 검증 완료 후 테스트 데이터셋을 기반으로 수치를 업데이트할 예정입니다. (나중에 아래 내용을 복사하여 본문에 반영하세요.)
[이미지 첨부: 단일 모델 사용 대비 가이드라인 준수율 상승, 처리 시간 단축 등을 비교한 막대 그래프]
```text
* 환각 및 규격 위반 감소: Critic 에이전트를 통한 자가 수정(Self-Correction) 루프 도입 전후 대비, 가이드라인 위반 및 논리적 오류 발생률 O% 감소.
* 토큰 소모량 최적화: 메타데이터 추출 및 VectorDB 기반 컨텍스트 주입(Context Injection) 적용으로 전체 파이프라인의 토큰 사용량 O% 절감.
* 처리 시간 단축: 기술 문서 1건당 아웃라인 설계, 초안 작성, 최종 윤문에 소요되는 End-to-End 처리 시간 O% 단축.
```
-->
---

## 기술 스택

- **Framework:** LangChain, LangGraph
- **Database:** ChromaDB (Vector Store), SQLite (Log Management)
- **LLM:** Google Gemini 3.1 Series
- **Frontend / Backend:** Streamlit / FastAPI (Planned)
- **Language:** Python 3.10+

---

## 프로젝트 구조

```text
autodoc_mas_project/
├── app.py                           # Streamlit 웹 UI 및 메인 실행 파일
├── requirements.txt                 # 패키지 의존성
├── docs/                            # 프로젝트 설계 가이드 및 마일스톤 문서
│   ├── 01_project_milestone.md
│   ├── 02_branch_guide.md
│   ├── 03_commit_message_guide.md
│   └── 04_prompt_guide.md
└── src/
    ├── graph.py                     # LangGraph StateGraph 및 워크플로우 정의
    ├── state.py                     # 공유 상태(TechDocState) 스키마 정의
    ├── memory.py                    # ChromaDB 초기화 및 컨텍스트 관리 로직
    ├── utils.py                     # 유틸리티 기능 (이미지 인코딩 등)
    └── nodes/                       # 에이전트 노드 구현부
        ├── main_node.py             # Supervisor, Critic, Final Agent
        └── sub_graph_nodes/         
            ├── intro_graph_node.py        # 신규 문서 전용 파이프라인
            ├── continuation_graph_node.py # 업데이트 문서 전용 파이프라인
            └── common_node.py             # 공통 기능 (다이어그램 분석 등)
