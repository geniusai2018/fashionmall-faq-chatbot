import os
from dotenv import load_dotenv

import streamlit as st

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


# ---------------------------
# 환경 설정
# ---------------------------
st.set_page_config(
    page_title="여성의류 쇼핑몰 FAQ 챗봇",
    page_icon="👗",
    layout="wide"
)

st.title("👗 여성의류 쇼핑몰 FAQ 챗봇")
st.caption("배송, 교환/반품, 결제, 회원혜택 등 자주 묻는 질문에 빠르게 답변합니다.")

# OpenAI API Key 입력
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error(".env 파일에 OPENAI_API_KEY를 설정해주세요.")
    st.stop()

DB_PATH = "faiss_db"


# ---------------------------
# 벡터 DB 로드 함수
# ---------------------------
@st.cache_resource
def load_vectorstore():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.load_local(
        DB_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )
    return vectorstore


# ---------------------------
# 문서 포맷 함수
# ---------------------------
def format_docs(docs):
    if not docs:
        return "관련 FAQ를 찾지 못했습니다."

    context_text = []
    for idx, doc in enumerate(docs, start=1):
        question = doc.metadata.get("question", "")
        answer = doc.metadata.get("answer", "")
        category = doc.metadata.get("category", "일반")
        context_text.append(
            f"[FAQ {idx}]\n"
            f"카테고리: {category}\n"
            f"질문: {question}\n"
            f"답변: {answer}\n"
        )
    return "\n".join(context_text)


# ---------------------------
# 체인 생성
# ---------------------------
def build_chain(vectorstore):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    prompt = ChatPromptTemplate.from_template(
        """
당신은 여성의류 쇼핑몰 고객센터 FAQ 챗봇입니다.

아래 검색된 FAQ 문맥만 바탕으로 답변하세요.
문맥에 없는 내용을 지어내지 마세요.
답변은 친절하고 간단명료하게 작성하세요.
질문과 가장 관련 높은 FAQ를 우선 반영하세요.
관련 FAQ가 없으면 "죄송합니다. 해당 문의에 대한 정확한 FAQ를 찾지 못했습니다."라고 답하세요.

[검색된 FAQ 문맥]
{context}

[사용자 질문]
{question}

[답변 작성 규칙]
1. 첫 문장에서 바로 핵심 답변을 말할 것
2. 필요하면 2~3문장으로 추가 설명할 것
3. 너무 길게 쓰지 말 것
4. 한국어로 자연스럽게 답할 것
"""
    )

    chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough()
        }
        | prompt
        | ChatOpenAI(model="gpt-5-nano", temperature=0)
    )

    return chain


# ---------------------------
# 사이드바 안내
# ---------------------------
with st.sidebar:
    
    st.subheader("예시 질문")
    st.write("- 배송은 얼마나 걸리나요?")
    st.write("- 교환 신청은 언제까지 가능한가요?")
    st.write("- 세일 상품도 반품되나요?")
    st.write("- 회원가입 혜택이 있나요?")


# ---------------------------
# 메인 실행
# ---------------------------
if not api_key:
    st.warning("왼쪽 사이드바에 OpenAI API Key를 입력해주세요.")
    st.stop()

try:
    vectorstore = load_vectorstore()
    chain = build_chain(vectorstore)
except Exception as e:
    st.error("벡터 DB를 불러오지 못했습니다. 먼저 `python vector_store.py`를 실행해주세요.")
    st.exception(e)
    st.stop()


# ---------------------------
# 채팅 상태 초기화
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요. 여성의류 쇼핑몰 FAQ 챗봇입니다. 궁금한 내용을 입력해주세요."
        }
    ]


# ---------------------------
# 이전 대화 출력
# ---------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ---------------------------
# 사용자 입력 처리
# ---------------------------
user_input = st.chat_input("예: 배송은 얼마나 걸리나요?")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("관련 FAQ를 검색하고 있습니다..."):
            try:
                response = chain.invoke(user_input)
                answer = response.content if hasattr(response, "content") else str(response)
            except Exception as e:
                answer = f"오류가 발생했습니다: {e}"

        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})