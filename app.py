import streamlit as st
import google.generativeai as genai

st.title("🛡️ 모델 이름 확인 도구")

# API 키 입력창
api_key = st.text_input("Gemini API Key를 입력하세요", type="password")

if st.button("사용 가능한 모델 목록 보기"):
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        model_names = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        st.success("연결 성공! 아래 모델 이름 중 하나를 복사해서 저에게 알려주세요:")
        st.write(model_names)
    except Exception as e:
        st.error(f"연결 실패: {e}")
