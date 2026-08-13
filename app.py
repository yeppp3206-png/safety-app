import streamlit as st
import chromadb
import google.generativeai as genai
from PIL import Image
from datetime import date
import os

st.set_page_config(page_title="현장 안전 AI", page_icon="🛡️")

st.title("🛡️ 현장 안전 AI")
st.caption("안전 법령, 인간공학 평가, 화학물질(MSDS) 관리 플랫폼")

# 1️⃣ 오늘 날짜 상단 표시
today = date.today().strftime("%Y년 %m월 %d일")
st.info(f"📅 오늘 날짜: {today}")

# 2️⃣ 사업장 종류 선택
industry_type = st.radio("📍 현재 사업장의 종류를 선택하세요:", ("제조업", "건설업", "기타"), horizontal=True)

# 새 API 키 적용
DEFAULT_API_KEY = "AQ.Ab8RN6I-ZlGk3t75sVY4BVRlpEajZ95DpOLb2_6qTZq39KDGQg"
api_key = st.sidebar.text_input("Gemini API Key", value=DEFAULT_API_KEY, type="password")

# ==========================================
# 💡 DB 구축 로직
# ==========================================
@st.cache_resource
def load_db():
    db_path = "./safety_db"
    client = chromadb.PersistentClient(path=db_path)
    try:
        return client.get_collection(name="safety_rules")
    except:
        collection = client.create_collection(name="safety_rules")
        file_list = ["법.txt", "시행령.txt", "시행규칙.txt", "안전보건기준.txt", "중대재해처벌법.txt"]
        all_docs = []
        for file_name in file_list:
            if os.path.exists(file_name):
                with open(file_name, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.read().split("\n\n") if len(line.strip()) > 10]
                    all_docs.extend([f"[{file_name.replace('.txt', '')}] {doc}" for doc in lines])
        if all_docs:
            collection.add(documents=all_docs, ids=[f"id_{i}" for i in range(len(all_docs))])
        return collection

with st.spinner("DB 로딩 중..."):
    collection = load_db()

# ==========================================
# 💡 가장 안정적인 gemini-1.5-flash 모델 직접 호출
# ==========================================
def get_ai_model():
    genai.configure(api_key=api_key)
    # 가장 범용적인 1.5-flash 모델 사용
    return genai.GenerativeModel("gemini-1.5-flash")

# 3개의 탭 구성
tab1, tab2, tab3 = st.tabs(["🔍 일반 위험 분석", "🧍‍♂️ 인간공학 평가", "🧪 화학물질(MSDS) 안전 관리"])

# 탭 1, 2, 3 동일...
with tab1:
    st.subheader("일반 위험 요소 분석")
    image_file = st.file_uploader("📷 현장 사진 업로드", type=["jpg", "jpeg", "png"], key="g1")
    context = st.text_area("✍️ 상황 설명", key="g2")
    if st.button("분석 시작", key="g3"):
        model = get_ai_model()
        # 검색
        res = collection.query(query_texts=[f"{industry_type} {context}"], n_results=1)
        rules = "\n".join(res['documents'][0])
        
        if image_file:
            image = Image.open(image_file)
            st.image(image)
            response = model.generate_content(["이 사진과 상황을 보고 안전 리포트를 작성하세요. 참고 법령: " + rules, image])
        else:
            response = model.generate_content(f"상황: {context}. 관련 법령: {rules}. 안전 리포트를 작성하세요.")
        st.success(response.text)

# 탭 2: 인간공학
with tab2:
    st.subheader("🧍‍♂️ 인간공학 평가")
    img_ergo = st.file_uploader("📷 자세 사진", type=["jpg", "jpeg", "png"], key="e1")
    if st.button("평가 시작", key="e2"):
        model = get_ai_model()
        image = Image.open(img_ergo)
        st.image(image)
        res = model.generate_content(["이 자세를 인간공학적으로 평가하고 개선안을 제시하세요.", image])
        st.success(res.text)

# 탭 3: MSDS
with tab3:
    st.subheader("🧪 화학물질 안전 관리")
    c_name = st.text_input("화학물질명")
    if st.button("분석 시작", key="c1"):
        model = get_ai_model()
        res = model.generate_content(f"'{c_name}' 물질의 위험성, 보호구, 누출 시 조치 요령을 작성하세요.")
        st.success(res.text)
