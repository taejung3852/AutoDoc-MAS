from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage
from src.utils import embeddings, writer_llm
import streamlit as st

load_dotenv()

text_splitter = CharacterTextSplitter(
    chunk_size = 500,
    chunk_overlap=100,
    separator='\n'
)

DB_DIR = "./chroma_db"
COLLECTION_NAME = "techdoc_memory"
@st.cache_resource
def get_vector_db():
    """ChromaDB 인스턴스를 초기화하고 반환합니다."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=DB_DIR
    )

def save_doc_context(system_name: str, context_text: str):
    """
    승인된 시스템 아키텍처 및 명세의 핵심 맥락을 VectorDB에 저장합니다.
    """
    db = get_vector_db()
    
    # Document 객체로 포장해서 저장 (메타데이터로 주제를 달아줍니다)
    raw_doc = Document(
        page_content=context_text,
        metadata={"system_name": system_name}
    )
    
    docs = text_splitter.split_documents([raw_doc])
    db.add_documents(docs)
    print(f"  -> VectorDB 저장 완료: [{system_name}]의 맥락이 기록되었습니다.")

def retrieve_past_context(system_name: str, k: int = 1) -> str:
    """
    업데이트 대상 시스템과 가장 유사한 과거 아키텍처 맥락을 VectorDB에서 검색합니다.
    """
    db = get_vector_db()
    
    # DB에 데이터가 있는지 먼저 확인
    if not db.get()['documents']:
         return "아직 저장된 이전 시스템 맥락이 없습니다."

    # 현재 주제(current_topic)를 쿼리로 날려서 가장 비슷한 과거 글을 찾기 
    sys_msg = f"""
    # Role
    당신은 시스템 아키텍처 VectorDB 검색 쿼리 최적화 전문가입니다.

    # Instructions
    주어진 '시스템명'을 바탕으로, 과거 데이터베이스에서 연관성 높은 기술 문서를 찾기 위한 '검색 키워드 묶음'을 생성하십시오.

    # Steps
    1. 시스템명에서 핵심이 되는 기술적 도메인이나 주요 기능을 유추하십시오.
    2. 해당 시스템과 빈번하게 연관되는 IT 기술 용어, 개념어, 또는 컴포넌트 이름을 3~5개 추출하십시오.

    # Expectations
    이 쿼리는 VectorDB에서 과거 아키텍처의 유사도 검색(Similarity Search)을 수행하는 데 직접적으로 사용됩니다.

    # Narrowing
    - 절대 문장 형태로 작성하지 마십시오. (예: "~에 대해 알려줘" 금지)
    - 오직 쉼표(,)로 구분된 단어들만 출력하십시오.
    
    [Format]
    키워드1, 키워드2, 키워드3
    """
    human_msg = f"""
    [시스템명]
    {system_name}
    """
    
    # 원래는 동적 변수는 sys_msg에 안넣지만 쿼리는 리트리버 쿼리는 그런 구분이 없어서 하나로 합침
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
        ])
    
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_query = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item) 
            for item in raw_content
        ).strip()
    else:
        raw_query = str(raw_content).strip()
        
    parsed_keywords = " ".join([word.strip() for word in raw_query.split(',') if word.strip()])

    query = parsed_keywords if parsed_keywords else system_name # 파싱 실패 시 기본 시스템명으로 폴백(Fallback)

    print(f"  -> 🔍 RAG 추출 검색 키워드: {query}")
    
    results = db.similarity_search(
        query,
        k=k,
        filter={'system_name': system_name}
    ) 
    
    if not results:
        return "관련된 이전 시스템 맥락을 찾지 못했습니다."
        
    # 검색된 문서들을 하나의 문자열로 취합
    context_list = []
    for i, doc in enumerate(results):
        sys_name = doc.metadata.get('system_name', '알 수 없는 시스템')
        context_list.append(f"[과거 시스템 {i+1} - {sys_name}]\n{doc.page_content}")
        
    return "\n\n".join(context_list)


def get_all_systems() -> list[str]:
    """VectorDB에 저장된 모든 고유 시스템명(system_name) 목록 불러오기"""
    db = get_vector_db() # 캐싱된 DB 호출
    try:
        # ChromaDB에서 모든 데이터의 메타데이터 불러오기
        collection = db._collection
        result = collection.get(include=["metadatas"])
        
        if not result or not result.get("metadatas"):
            return []
            
        # 메타데이터에서 'system_name' 키의 값만 추출하여 중복 제거
        systems = set()
        for metadata in result["metadatas"]:
            if metadata and "system_name" in metadata:
                systems.add(metadata["system_name"])
                
        return list(systems)
    except Exception as e:
        print(f"시스템 목록 로드 중 에러 발생: {e}")
        return []

def delete_system(system_name: str) -> bool:
    """VectorDB에서 특정 시스템의 모든 데이터를 삭제합니다."""
    db = get_vector_db()
    try:
        collection = db._collection
        # metadata의 'system_name' 필드가 일치하는 데이터 모두 삭제 streamlit에서 해당 시스템 이름을 지운다고 버튼을 누르면 실행
        collection.delete(where={"system_name": system_name})
        print(f"🗑️ [System] '{system_name}' 관련 데이터가 ChromaDB에서 삭제되었습니다.")
        return True
    except Exception as e:
        print(f"시스템 데이터 삭제 중 에러 발생: {e}")
        return False

def save_user_guideline(system_name: str, guideline: str):
    """사용자가 지적한 기술적/구조적 피드백을 다음 작성을 위해 저장합니다."""
    # Context Injection 단계에서 과거 요약본과 함께 검색될 수 있도록 메타데이터와 함께 저장
    save_doc_context(
        system_name=system_name, 
        context_text=f"[사용자 피드백/가이드라인 절대 준수]\n{guideline}"
    )
    