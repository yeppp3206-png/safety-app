import streamlit as st
import chromadb
import google.generativeai as genai
from PIL import Image
from datetime import date
import os

st.set_page_config(page_title="현장 안전 AI", page_icon="🛡️")

st.title("🛡️ 현장 안전 AI")
st.caption("안전 법령, 인간공학 평가, 화학물질(MSDS) 관리까지 책임지는 현장 맞춤형 AI 솔루션입니다.")

# 1️⃣ 오늘 날짜 상단 표시
today = date.today().strftime("%Y년 %m월 %d일")
st.info(f"📅 오늘 날짜: {today}")

# 2️⃣ 사업장 종류 선택
industry_type = st.radio(
    "📍 현재 사업장의 종류를 선택하세요:",
    ("제조업", "건설업", "기타"),
    horizontal=True
)

# API 키 설정
DEFAULT_API_KEY = "AQ.Ab8RN6KMGCo5J8I3VWzSagqowvPwr4Oyxo2VZSzuN7KGRJPKpA"
api_key_input = st.sidebar.text_input("Gemini API Key", value=DEFAULT_API_KEY, type="password")
api_key = api_key_input.strip() if api_key_input else DEFAULT_API_KEY

# ==========================================
# 💡 DB 자동 구축 로직 (에러 차단)
# ==========================================
@st.cache_resource
def load_db():
    db_path = "./safety_db"
    client = chromadb.PersistentClient(path=db_path)
    
    try:
        # 기존 데이터베이스 확인
        collection = client.get_collection(name="safety_rules")
        if collection.count() == 0:
            raise ValueError("데이터베이스가 비어있습니다.")
        return collection
    except Exception:
        # 새로 구축
        collection = client.get_or_create_collection(name="safety_rules")
        file_list = ["법.txt", "시행령.txt", "시행규칙.txt", "안전보건기준.txt", "중대재해처벌법.txt"]
        all_documents = []
        
        for file_name in file_list:
            if os.path.exists(file_name):
                with open(file_name, "r", encoding="utf-8") as f:
                    content = f.read()
                raw_documents = content.split("\n\n")
                law_title = file_name.replace(".txt", "")
                for doc in raw_documents:
                    doc = doc.strip()
                    if len(doc) > 10:
                        all_documents.append(f"[{law_title}] {doc}")
        
        if all_documents:
            ids = [f"rule_v6_{i+1}" for i in range(len(all_documents))]
            collection.add(documents=all_documents, ids=ids)
        return collection

# 로딩 인디케이터
with st.spinner("데이터베이스를 준비 중입니다..."):
    try:
        collection = load_db()
    except Exception as e:
        st.error(f"⚠️ 데이터베이스 초기화 실패: {e}")
        st.stop()

# ==========================================
# 💡 AI 모델 강제 고정 (429 에러 방지)
# ==========================================
def get_ai_model():
    genai.configure(api_key=api_key)
    # 가장 안정적이고 넉넉한 1.5-flash 모델로 강제 고정
    return genai.GenerativeModel("gemini-1.5-flash")

# 3개의 탭 구성
tab1, tab2, tab3 = st.tabs(["🔍 일반 위험 분석", "🧍‍♂️ 인간공학 평가", "🧪 화학물질(MSDS) 안전 관리"])

# 탭 1: 일반 위험 분석
with tab1:
    st.subheader("일반 위험 요소 분석")
    image_file = st.file_uploader("📷 현장 사진 업로드 (선택사항)", type=["jpg", "jpeg", "png"], key="general_img")
    context_input = st.text_area("✍️ 상황 설명 또는 키워드 입력", key="general_text")

    if st.button("위험 분석 시작", type="primary", key="general_btn"):
        with st.spinner("AI 분석 중..."):
            model = get_ai_model()
            if image_file:
                image = Image.open(image_file)
                st.image(image, use_container_width=True)
                results = collection.query(query_texts=[f"{industry_type} {context_input}"], n_results=2)
                matched_rules = "\n\n".join(results['documents'][0])
                prompt = f"이 사진과 상황({context_input})을 {industry_type} 안전 관점에서 분석하고 리포트를 작성하세요. [법령]: {matched_rules}"
                response = model.generate_content([prompt, image])
                st.success(response.text)
            else:
                results = collection.query(query_texts=[f"{industry_type} {context_input}"], n_results=2)
                matched_rules = "\n\n".join(results['documents'][0])
                response = model.generate_content(f"'{context_input}' 상황에 대해 안전 리포트를 작성하세요. [법령]: {matched_rules}")
                st.success(response.text)

# 탭 2: 인간공학
with tab2:
    st.subheader("🧍‍♂️ 인간공학 평가")
    image_ergo = st.file_uploader("📷 자세 사진 업로드", type=["jpg", "jpeg", "png"], key="ergo_img")
    if st.button("인간공학 분석 시작", type="primary", key="ergo_btn"):
        with st.spinner("분석 중..."):
            model = get_ai_model()
            image = Image.open(image_ergo)
            st.image(image, use_container_width=True)
            response = model.generate_content(["이 작업자의 자세를 OWAS/REBA 기법으로 평가하고 개선안을 제시하세요.", image])
            st.success(response.text)

# 탭 3: 화학물질
with tab3:
    st.subheader("🧪 화학물질 안전 관리")
    c_name = st.text_input("화학물질명")
    if st.button("안전 분석 시작", type="primary", key="chem_btn"):
        with st.spinner("분석 중..."):
            model = get_ai_model()
            response = model.generate_content(f"화학물질 '{c_name}'에 대한 MSDS 기반 위험성, 필수 보호구, 누출 시 조치 요령을 작성하세요.")
            st.success(response.text)
