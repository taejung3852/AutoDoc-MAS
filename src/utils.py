import os
import base64
import ast
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# ==============================================
# LLM 정의
writer_llm = ChatGoogleGenerativeAI(model = 'gemini-3.1-flash-lite', temperature=0.4)
critic_llm = ChatGoogleGenerativeAI(model = 'gemini-3.1-flash-lite', temperature=0)

# ==============================================
# Embedding 모델 정의
embeddings = GoogleGenerativeAIEmbeddings(model ="gemini-embedding-001")

def load_technical_source(path_or_text: str) -> str:
    """원시 기술 데이터가 파일 경로일 경우 읽어오고, 아니면 텍스트 그대로 반환"""
    if isinstance(path_or_text, str) and os.path.exists(path_or_text):
        with open(path_or_text, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    return path_or_text


def encode_image_to_base64(image_path: str):
    """이미지 파일 경로를 받아 Base64 문자열로 변환합니다."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    else:
        print(f"⚠️ 경고: 이미지를 찾을 수 없습니다 -> {image_path}")
        return None


def extract_tech_doc_style(sample_text: str) -> str:
    """사내 기술 문서 샘플을 분석하여 AI용 '스타일 가이드라인(doc_style_guide)'을 자동 추출합니다."""
    
    sys_msg = """
    # Role
    당신은 기업 기술 문서의 톤앤매너와 포맷팅을 분석하여 AI 가이드라인을 설계하는 수석 테크니컬 라이터입니다.

    # Instructions
    주어진 사내 기술 문서 샘플을 분석하여, 다른 AI 에이전트가 완벽히 동일한 포맷과 어투로 문서를 작성할 수 있도록 '스타일 행동 지침'을 도출하십시오.

    # Steps
    1. 문서 샘플을 정독하며 주로 사용된 어조(예: 3인칭, 건조한 문체), 종결 어미(예: ~합니다, ~함), 문장 길이 등의 텍스트 특징을 분석하십시오.
    2. 마크다운 헤딩(#), 불릿 포인트(-), 코드 블록 등 구조적으로 자주 사용된 포맷팅 규칙을 식별하십시오.
    3. 분석된 어조와 구조 규칙을 종합하여, 다른 AI가 읽고 즉각적으로 따를 수 있는 명령형 지침으로 정리하십시오.

    # Expectations
    이 지침은 후속 AI 에이전트들의 시스템 프롬프트(System Message)에 직접 주입됩니다. 따라서 해석의 여지 없이 매우 명확하고 구체적인 규칙 형태여야 합니다.

    # Narrowing
    - 절대 샘플 문서의 기술적 내용(Content)이나 도메인 지식을 요약하지 마십시오. 오직 '문장 스타일과 구조 규칙'만 추출하십시오.
    - 감성적인 표현을 배제하고, 객관적이고 건조한 어조로 작성하십시오.
    - 출력은 반드시 다른 AI에게 지시하는 형태의 3문장 이내 명령형 문장(예: "~하십시오.")으로만 구성하십시오.
    """
    
    human_msg = f"""
    [사내 기술 문서 샘플]
    {sample_text}
    """
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return response.content


def synthesize_tech_feedback(edited_text: str, tech_feedback: str, compliance_feedback: str) -> dict:
    """
    사용자의 최종 수정본(행동)과 명시적 피드백(말)을 분석하여,
    다음 에이전트가 사용할 통합된 톤앤매너 및 구조 가이드라인을 생성합니다.
    """
    
    sys_msg = """
    # Role
    당신은 사용자의 문서 피드백을 AI 시스템의 프롬프트 규칙으로 변환하는 수석 프롬프트 엔지니어입니다.

    # Instructions
    수정된 최종 기술 문서와 사용자가 입력한 피드백(기술적/규격적)을 종합하여, 향후 AI가 문서를 작성할 때 반드시 지켜야 할 [기술 서술 지침]과 [포맷 지침]을 생성하십시오.

    # Steps
    1. 사용자가 직접 수정한 최종 문서의 문체, 어조, 포맷(암묵적 피드백)을 분석하십시오.
    2. 사용자가 텍스트로 남긴 명시적인 피드백(기술적 팩트 지적, 규격 지적)을 분석하십시오.
    3. 위 두 가지를 종합하여, 다른 AI 에이전트가 즉시 이해하고 적용할 수 있는 명확한 명령형 문장의 지침으로 요약하십시오.

    # Expectations
    생성된 지침은 향후 문서 작성 파이프라인에서 핵심 컨텍스트로 주입되어, 동일한 수정 사항이나 실수가 반복되지 않도록 시스템을 방어하는 역할을 해야 합니다.

    # Narrowing
    - 절대 부연 설명이나 마크다운 코드 블록(```)을 사용하지 마십시오.
    - 반드시 파이썬 딕셔너리(Dictionary) 형식으로만 출력하십시오.
    
    [Format]
    {"technical_rule": "(기술 및 팩트 관련 행동 지침)", "compliance_rule": "(문체 및 포맷 관련 행동 지침)"}
    """

    # 글이 너무 길 경우 토큰 절약을 위해 앞부분과 뒷부분 일부만 잘라서 제공
    text_sample = edited_text if len(edited_text) < 1500 else edited_text[:1000] + "\n...[중략]...\n" + edited_text[-500:]

    human_msg = f"""
    [사용자가 수정한 최종 완성본]
    {text_sample}
    [기술적 팩트 피드백]: {tech_feedback if tech_feedback else '없음'}
    [포맷/구조 피드백]: {compliance_feedback if compliance_feedback else '없음'}
    """
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])

    raw_content = response.content
    if isinstance(raw_content, list):
        clean_text = "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item) 
            for item in raw_content
        )
    else:
        clean_text = str(raw_content)
    
    try:
        return ast.literal_eval(clean_text.strip())
    except (ValueError, SyntaxError) as e:
        print(f'❌ 파싱 에러 발생: {e}. 기본 딕셔너리를 반환합니다.')
        return {"technical_rule": "", "compliance_rule": clean_text}

