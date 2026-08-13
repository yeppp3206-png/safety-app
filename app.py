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
        collection = client.get_collection(name="safety_rules")
        if collection.count() == 0:
            raise ValueError("데이터베이스가 비어있습니다.")
        return collection
    except Exception:
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
            ids = [f"rule_v7_{i+1}" for i in range(len(all_documents))]
            collection.add(documents=all_documents, ids=ids)
        return collection

with st.spinner("데이터베이스를 준비 중입니다..."):
    try:
        collection = load_db()
    except Exception as e:
        st.error(f"⚠️ 데이터베이스 초기화 실패: {e}")
        st.stop()

# ==========================================
# 💡 AI 모델 설정 (models/ 경로 명시로 NotFound 에러 차단)
# ==========================================
def get_ai_model():
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("models/gemini-1.5-flash")

# 3개의 탭 구성
tab1, tab2, tab3 = st.tabs(["🔍 일반 위험 분석", "🧍‍♂️ 인간공학 평가", "🧪 화학물질(MSDS) 안전 관리"])

# ==========================================
# 탭 1: 일반 위험 분석
# ==========================================
with tab1:
    st.subheader("일반 위험 요소 분석")
    image_file = st.file_uploader("📷 현장 사진 업로드 (선택사항)", type=["jpg", "jpeg", "png"], key="general_img")
    context_input = st.text_area("✍️ 상황 설명 또는 키워드 입력", key="general_text")

    if st.button("위험 분석 시작", type="primary", key="general_btn"):
        if not image_file and not context_input.strip():
            st.warning("⚠️ 사진을 업로드하거나 상황 설명을 입력해 주세요!")
        else:
            try:
                with st.spinner("AI 분석 중..."):
                    model = get_ai_model()
                    keyword = context_input.strip() if context_input else "일반 안전"
                    results = collection.query(query_texts=[f"{industry_type} {keyword}"], n_results=2)
                    matched_rules = "\n\n".join(results['documents'][0])
                    
                    if image_file:
                        image = Image.open(image_file)
                        st.image(image, caption="업로드된 사진", use_container_width=True)
                        prompt = f"""
                        [사업장 종류]: {industry_type}
                        [추가 상황 설명]: {context_input}
                        [관련 법령 (검색결과)]: {matched_rules}
                        위 사진과 내용을 바탕으로 현장 안전 리포트를 아래 양식으로 작성하세요:
                        ### 1. 🗣️ 근로자 현장 계도 멘트 (친근하고 경각심을 주는 구어체)
                        ### 2. 📜 위반/관련 법조항 및 근거
                        ### 3. 🚨 위반 시 불이익 (과태료, 처벌 등)
                        ### 4. 🛠️ 권장 시정 조치
                        """
                        response = model.generate_content([prompt, image])
                        st.markdown("---")
                        st.success(response.text)
                    else:
                        prompt = f"""
                        [사업장 종류]: {industry_type}
                        [검색 키워드/상황]: {context_input}
                        [관련 법령 (검색결과)]: {matched_rules}
                        위 내용을 바탕으로 현장 안전 안내서를 아래 양식으로 작성하세요:
                        ### 1. 📜 관련 법조항 요약 및 근거
                        ### 2. ⚠️ 자주 발생하는 잘못된 행동/상태 예시 (2가지)
                        ### 3. 🚨 위반 시 불이익 (과태료, 법적 처벌 등)
                        ### 4. 🛠️ 권장 시정 조치 및 안전 수칙
                        ### 5. 🗣️ 근로자 현장 계도 멘트 (친근한 구어체)
                        """
                        response = model.generate_content(prompt)
                        st.markdown("---")
                        st.success(response.text)
            except Exception as e:
                st.error(f"❌ 분석 중 오류 발생:\n\n{e}")

# ==========================================
# 탭 2: 인간공학 평가
# ==========================================
with tab2:
    st.subheader("🧍‍♂️ 작업자 자세 인간공학(Ergonomics) 평가")
    image_ergo = st.file_uploader("📷 작업자 자세 사진 업로드", type=["jpg", "jpeg", "png"], key="ergo_img")
    
    if image_ergo is not None:
        image = Image.open(image_ergo)
        st.image(image, caption="분석 대상 작업자 사진", use_container_width=True)
        
        if st.button("인간공학 분석 시작", type="primary", key="ergo_btn"):
            try:
                with st.spinner("자세 부하 분석 중..."):
                    model = get_ai_model()
                    prompt = "당신은 인간공학 전문가입니다. 사진 속 작업자의 자세를 OWAS 또는 REBA/RULA 기법 관점에서 평가하고, 신체 부위별 부하 분석 및 작업환경 개선 대책을 리포트로 작성하세요."
                    response = model.generate_content([prompt, image])
                    st.markdown("---")
                    st.success(response.text)
            except Exception as e:
                st.error(f"❌ 분석 중 오류 발생:\n\n{e}")

# ==========================================
# 탭 3: 화학물질(MSDS) 안전 관리
# ==========================================
with tab3:
    st.subheader("🧪 화학물질(MSDS) 안전 및 설비 누출 대응")
    c_name = st.text_input("화학물질명 입력 (예: 톨루엔, 황산)")
    
    if st.button("화학물질 안전 분석 시작", type="primary", key="chem_btn"):
        if not c_name:
            st.warning("⚠️ 화학물질명을 입력해 주세요!")
        else:
            try:
                with st.spinner("MSDS 및 설비 위험성 분석 중..."):
                    model = get_ai_model()
                    prompt = f"""
                    당신은 산업위생관리 및 화학설비안전 전문가입니다.
                    화학물질 '{c_name}'에 대하여 아래 양식으로 리포트를 작성하세요:
                    ### 1. ☠️ 유해성·위험성 요약 (GHS 기준)
                    ### 2. 🥽 필수 개인보호구(PPE) 및 보건 조치
                    ### 3. 🏭 설비 안전 및 취급 시 주의사항
                    ### 4. 🚨 누출 시 응급조치 요령
                    """
                    response = model.generate_content(prompt)
                    st.markdown("---")
                    st.success(response.text)
            except Exception as e:
                st.error(f"❌ 분석 중 오류 발생:\n\n{e}")
