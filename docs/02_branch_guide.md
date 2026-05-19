# Git Branch 전략


이 문서는 본 프로젝트의 코드 독립성과 버전 관리를 위한 가이드라인. 모든 작업은 별도의 브랜치에서 진행, 검증 후 `master` 브랜치에 병합한다.
(개발하면서 내가 참고하기 위해 정리)

---

## 1. 브랜치 구조 및 전략

- **`master` 브랜치**: 언제든 배포 및 실행이 가능한 최신 상태의 코드만 존재
- **`작업 브랜치`**: 기능 개발, 버그 수정 등 모든 변경 사항은 `master`에서 분기한 개별 브랜치

---

## 2. 브랜치 명명 규칙
브랜치 이름은 소문자 키워드와 간결한 설명을 조합하여 생성

| 키워드 | 용도 | 예시 |
| :--- | :--- | :--- |
| **`feat/`** | 새로운 기능 구현 | `feat/state-definition` |
| **`fix/`** | 버그 및 오류 수정 | `fix/graph-loop-error` |
| **`docs/`** | 문서 작성 및 수정 | `docs/update-readme` |
| **`refactor/`** | 기능 변경 없는 코드 구조 개선 | `refactor/modularize-nodes` |
| **`test/`** | 테스트 코드 추가 및 수정 | `test/dummy-node-verification` |
| **`chore/`** | 빌드 업무, 패키지 설정, 에셋 파일 이동 등 | `chore/move-assets-folder` |

---

## 3. 상세 작업 흐름

### 단계 1: 최신 코드 확보
작업을 하기 전, 반드시 `master` 브랜치를 최신 상태로 갱신
```bash
git checkout master
git pull origin master
```

### 단계 2: 작업 브랜치 생성
구현할 기능에 맞는 이름을 지정하여 브랜치를 생성하고 이동
```bash
# 예: 컨텍스트 인젝션 노드 개발
git checkout -b feat/context-injection
```

### 단계 3: 코드 수정 및 커밋
논리적으로 완결된 단위마다 커밋
```bash
git add .
git commit -m "feat: 컨텍스트 주입 노드 기본 로직 구현"
```

### 단계 4: 원격 저장소 푸시 및 PR 생성
작업이 완료된 브랜치를 원격에 올리고, GitHub 등에서 Pull Request(PR)를 생성
```bash
git push origin feat/phase0-context-injection
# 이후 GitHub UI에서 'Compare & pull request' 버튼 클릭하여 PR 생성
```

### 단계 5: 검토 및 병합 (Merge)
PR에서 변경 사항을 최종 확인한 후, 이상이 없으면 master로 병합(Merge)을 승인

### 단계 6: 로컬 동기화 및 브랜치 삭제
병합이 완료되면 로컬의 master를 최신화하고 사용한 브랜치는 삭제
```bash
# 1. 로컬 master 최신화
git checkout master
git pull origin master

# 2. 로컬 브랜치 삭제
git branch -d feat/context-injection

# 3. 원격 브랜치 삭제
git push origin --delete feat/context-injection
```

## 4. 주의사항

- 단일 책임: 하나의 브랜치가 여러 기능을 동시에 수정 X

- 수시 커밋: 커밋 하나가 너무 크면 리뷰가 어렵다. 의미 있는 단위로 쪼개기

- 병합 전 테스트: PR을 승인하기 전에 반드시 로컬 혹은 테스트 환경에서 정상 작동 여부를 확인

- PR 활용: 혼자 작업하더라도 PR의 'Files changed' 탭을 통해 셀프 코드 리뷰를 진행할 것

- 충돌 해결: PR에 충돌이 발생하면 반드시 로컬에서 해결하고 다시 푸시한 뒤 리뷰를 요청한다.