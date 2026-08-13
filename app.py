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

# API 키 설정 (새로 발급받으신 키 반영)
DEFAULT_API_KEY = "AQ.Ab8RN6I-ZlGk3t75sVY4BVRlpEajZ95DpOLb2_6qTZq39KDGQg"
api_key_input = st.sidebar.text_input("Gemini API Key", value=DEFAULT_API_KEY, type="password")
api_key = api_key_input.strip() if api_key_input else DEFAULT_API_KEY

# ==========================================
# 💡 UI 요소를 완전히 배제하여 에러를 차단한 DB 로직
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
        print("⚠️ 법령 데이터베이스를 처음 구축하는 중입니다...")
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
            ids = [f"rule_v5_{i+1}" for i in range(len(all_documents))]
            collection.add(documents=all_documents, ids=ids)
            print("✅ 데이터베이스 구축 완료!")
        else:
            print("⚠️ 깃허브 창고에 법령 텍스트 파일(법.txt 등)이 없습니다!")
            
        return collection

with st.spinner("법령 데이터베이스를 점검 및 준비 중입니다... (최초 1회 약 30초 소요)"):
    try:
        collection = load_db()
    except Exception as e:
        st.error(f"⚠️ 데이터베이스 로드 중 알 수 없는 오류 발생: {e}")
        st.stop()

# ==========================================
# 💡 404 에러 원천 차단형 실시간 Fallback 호출 함수
# ==========================================
def call_gemini(contents):
    genai.configure(api_key=api_key)
    # gemini-2.0-flash를 최우선으로 시도하고 실패 시 순차적으로 대체
    candidates = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
    
    last_err = None
    for m_name in candidates:
        try:
            model = genai.GenerativeModel(m_name)
            return model.generate_content(contents)
        except Exception as e:
            last_err = e
            continue
            
    raise Exception(f"모든 AI 모델 호출에 실패했습니다. (마지막 에러: {last_err})")

# 3개의 탭 구성
tab1, tab2, tab3 = st.tabs(["🔍 일반 위험 분석", "🧍‍♂️ 인간공학 평가", "🧪 화학물질(MSDS) 안전 관리"])

# ==========================================
# 탭 1: 일반 위험 분석하기
# ==========================================
with tab1:
    st.subheader("일반 위험 요소 분석")
    image_file = st.file_uploader("📷 현장 사진 업로드 (선택사항)", type=["jpg", "jpeg", "png"], key="general_img")
    context_input = st.text_area(
        "✍️ 상황 설명 또는 키워드 입력 (선택사항)", 
        placeholder="사진을 설명하거나 검색할 키워드를 자유롭게 적어주세요.",
        key="general_text"
    )

    if st.button("위험 분석 시작", type="primary", key="general_btn"):
        if not image_file and not context_input.strip():
            st.warning("⚠️ 사진을 업로드하거나 상황 설명을 입력해 주세요!")
        else:
            try:
                with st.spinner("AI가 상황을 분석하고 법령을 찾는 중..."):
                    if image_file:
                        image = Image.open(image_file)
                        st.image(image, caption="업로드된 사진", use_container_width=True)
                        
                        context_prompt = f"이 사진의 추가 상황 설명: {context_input}" if context_input.strip() else "추가 설명 없음."
                        prompt_vision = f"당신은 {industry_type} 산업안전 전문가입니다. 사진 속 위험한 행동이나 설비 상태를 분석하세요. [추가 상황 설명]: {context_prompt}. 이를 종합하여 2문장으로 간결하게 요약하세요."
                        
                        vision_response = call_gemini([prompt_vision, image])
                        detected_risk = vision_response.text
                        st.info(f"**[탐지된 위험 요소]**\n\n{detected_risk}")
                        
                        results = collection.query(query_texts=[f"{industry_type} {detected_risk}"], n_results=2)
                        matched_rules = "\n\n".join(results['documents'][0])
                        
                        prompt_report = f"""
                        [사업장 종류]: {industry_type}
                        [위험 상황 요약]: {detected_risk}
                        [관련 법령 (검색결과)]: {matched_rules}
                        
                        위 내용을 바탕으로 현장 지도 리포트를 아래 양식으로 작성하세요.
                        ### 1. 🗣️ 근로자 현장 계도 멘트 (친근하고 경각심을 주는 구어체, 최우선 출력)
                        ### 2. 📜 위반/관련 법조항 및 근거
                        ### 3. 🚨 위반 시 불이익 (과태료, 처벌 등)
                        ### 4. 🛠️ 권장 시정 조치
                        """
                        report_response = call_gemini(prompt_report)
                        st.markdown("---")
                        st.success(report_response.text)
                    
                    else:
                        search_keyword = context_input.strip()
                        results = collection.query(query_texts=[f"{industry_type} {search_keyword}"], n_results=2)
                        matched_rules = "\n\n".join(results['documents'][0])
                        
                        prompt_keyword = f"""
                        [사업장 종류]: {industry_type}
                        [입력된 상황/키워드]: {search_keyword}
                        [관련 법령 (검색결과)]: {matched_rules}
                        
                        정보 전달에 초점을 맞춰 아래 양식으로 안내서를 작성하세요.
                        ### 1. 📜 관련 법조항 요약 및 근거 (가장 최우선 배치)
                        ### 2. ⚠️ 자주 발생하는 잘못된 행동/상태 예시 (2가지)
                        ### 3. 🚨 위반 시 불이익 (과태료, 법적 처벌 등)
                        ### 4. 🛠️ 권장 시정 조치 및 안전 수칙
                        ### 5. 🗣️ 근로자 현장 계도 멘트 (친근한 구어체)
                        """
                        keyword_response = call_gemini(prompt_keyword)
                        st.info(f"**['{search_keyword}'] 관련 분석 결과**")
                        st.markdown("---")
                        st.success(keyword_response.text)
                        
            except Exception as e:
                st.error(f"❌ 분석 중 오류 발생:\n\n{e}")

# ==========================================
# 탭 2: 인간공학적 자세 평가
# ==========================================
with tab2:
    st.subheader("🧍‍♂️ 작업자 자세 인간공학(Ergonomics) 분석")
    st.caption("사진과 현장 정보를 종합하여 가장 적합한 인간공학 기법(OWAS/REBA/RULA)으로 평가합니다.")
    
    image_file_ergo = st.file_uploader("📷 작업자 자세 사진 업로드", type=["jpg", "jpeg", "png"], key="ergo_img")
    
    col1, col2 = st.columns(2)
    with col1:
        load_weight = st.number_input("🏋️ 취급 중량(kg)", min_value=0.0, value=0.0, step=1.0)
        grip_status = st.selectbox("✋ 손잡이(그립) 상태", ["좋음 (손잡이 있음)", "보통 (손잡이 없으나 잡기 수월함)", "나쁨 (잡기 불편함/미끄러움)"])
    with col2:
        work_frequency = st.selectbox("⏱️ 작업 빈도/형태", ["정적 자세 (1분 이상 유지)", "간헐적 작업 (가끔 수행)", "반복 작업 (분당 4회 이상)"])
        vibration_status = st.selectbox("📳 진동 및 급격한 힘", ["없음", "진동 발생 (전동공구 등)", "급격한 힘 요구됨"])
    
    if image_file_ergo is not None:
        image_ergo = Image.open(image_file_ergo)
        st.image(image_ergo, caption="분석 대상 작업자 사진", use_container_width=True)
        
        if st.button("인간공학 정밀 분석 시작", type="primary", key="ergo_btn"):
            try:
                with st.spinner("AI가 작업 부하 인자들을 종합하여 정밀 평가표를 작성 중입니다..."):
                    prompt_ergo = f"""
                    당신은 {industry_type} 현장의 인간공학(Ergonomics) 전문가입니다.
                    사진과 아래의 [작업 부하 및 환경 정보]를 바탕으로 'OWAS', 'REBA', 'RULA' 중 가장 적합한 기법을 하나 선택하세요.
                    
                    [작업 부하 및 환경 정보]
                    - 취급 중량: {load_weight} kg
                    - 작업 빈도/형태: {work_frequency}
                    - 손잡이(그립) 상태: {grip_status}
                    - 진동/급격한 힘: {vibration_status}

                    아래 양식에 맞춰 전문적인 리포트를 작성하세요:
                    ### 1. 📏 선정된 평가 기법 및 이유
                    ### 2. 🦴 신체 부위별 부하 및 추가 인자 분석
                    ### 3. 📊 추정 조치 단계 (Action Level) - [마크다운 표 포함]
                    ### 4. 🛠️ 인간공학적 작업환경 개선 대책
                    """
                    
                    ergo_response = call_gemini([prompt_ergo, image_ergo])
                    
                    st.info(f"**[적용된 현장 인자]** 무게: {load_weight}kg | 빈도: {work_frequency} | 그립: {grip_status} | 진동: {vibration_status}")
                    st.markdown("---")
                    st.success(ergo_response.text)
                    
            except Exception as e:
                st.error(f"❌ 분석 중 오류 발생:\n\n{e}")

# ==========================================
# 탭 3: 화학물질(MSDS) AI 어드바이저
# ==========================================
with tab3:
    st.subheader("🧪 맞춤형 화학물질(MSDS) 안전 및 설비 누출 대응")
    st.caption("화학물질 정보와 작업 환경을 입력하면, 보건 조치와 설비 안전 대책을 통합 분석해 드립니다.")
    
    image_file_chem = st.file_uploader("📷 용기 라벨/GHS 마크 사진 업로드 (선택)", type=["jpg", "jpeg", "png"], key="chem_img")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        chem_name = st.text_input("화학물질명 (예: 톨루엔, 황산)", placeholder="화학물질 이름을 입력하세요")
        chem_conc = st.text_input("사용 농도 (%)", placeholder="예: 98% (모르면 '모름' 입력)")
    with col_c2:
        work_env = st.selectbox("작업/설비 환경", ["밀폐 공간 (탱크 내부 등)", "실내 (환기 불량)", "실내 (국소배기장치 있음)", "실외 (개방된 장소)"])
        work_temp = st.selectbox("공정 온도", ["상온 (일반 온도)", "고온 (가열 공정 등)"])

    if st.button("화학물질 안전 분석 시작", type="primary", key="chem_btn"):
        if not chem_name:
            st.warning("⚠️ 화학물질명을 입력해 주세요!")
        else:
            try:
                with st.spinner(f"'{chem_name}'의 유해성(보건) 및 설비 위험성을 종합 분석 중입니다..."):
                    prompt_chem = f"""
                    당신은 산업위생관리 및 화학설비안전 최고 전문가입니다.
                    아래 제공된 화학물질 정보와 작업 환경(설비 상태)을 종합하여 현장 맞춤형 MSDS 브리핑을 작성하세요.

                    [화학물질 및 작업 환경 정보]
                    - 화학물질명: {chem_name}
                    - 농도: {chem_conc}
                    - 작업 환경: {work_env}
                    - 공정 온도: {work_temp}

                    아래 양식에 맞춰 전문적이고 직관적인 리포트를 작성하세요:

                    ### 1. ☠️ 유해성·위험성 요약 (GHS 기준)
                    ### 2. 🥽 필수 개인보호구(PPE) 및 보건 조치
                    ### 3. 🏭 설비 안전 및 취급 시 주의사항
                    ### 4. 🚨 누출 시 응급조치 요령
                    """
                    
                    if image_file_chem:
                        image_chem = Image.open(image_file_chem)
                        chem_response = call_gemini([prompt_chem, image_chem])
                    else:
                        chem_response = call_gemini(prompt_chem)
                    
                    st.info(f"**[분석 대상]** 물질: {chem_name} ({chem_conc}) | 환경: {work_env} | 온도: {work_temp}")
                    st.markdown("---")
                    st.success(chem_response.text)
                    
            except Exception as e:
                st.error(f"❌ 분석 중 오류 발생:\n\n{e}")
