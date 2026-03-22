import json
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# .env 파일 로드
load_dotenv()

FAQ_JSON_PATH = "faq_data.json"
DB_PATH = "faiss_db"


def load_faq_data():
    """FAQ JSON 파일 읽기"""
    with open(FAQ_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_api_key():
    """OPENAI_API_KEY 존재 여부 확인"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            ".env 파일에 OPENAI_API_KEY=본인키 형태로 작성해주세요."
        )
    return api_key


def build_vectorstore():
    """FAQ 데이터를 임베딩하여 FAISS 벡터 DB 생성"""
    validate_api_key()
    data = load_faq_data()

    texts = []
    metadatas = []

    for item in data:
        question = item["question"]
        answer = item["answer"]
        category = item.get("category", "일반")

        # 질문 + 답변을 함께 임베딩해서 검색 정확도 향상
        text_for_embedding = f"질문: {question}\n답변: {answer}"

        texts.append(text_for_embedding)
        metadatas.append(
            {
                "id": item["id"],
                "question": question,
                "answer": answer,
                "category": category,
            }
        )

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
    )

    vectorstore.save_local(DB_PATH)
    print(f"벡터 DB 생성 완료: {DB_PATH}")


if __name__ == "__main__":
    build_vectorstore()