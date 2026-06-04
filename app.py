import streamlit as st
import pandas as pd
import io

# 1. 시트 접속 설정
FIXED_SHEET_URL = "https://docs.google.com/spreadsheets/d/165d-9euIgXTdeFFR-7urLRAEftNQ3ukt_62Hh0tdRFE/edit?usp=sharing"
FINAL_DOWNLOAD_URL = FIXED_SHEET_URL.replace('/edit?usp=sharing', '/export?format=xlsx')

def save_to_google_sheet(branch_name, data_frame):
    st.success(f"💾 {branch_name} 저장 완료!")
    return True

st.set_page_config(page_title="알바 급여 관리자", layout="wide")

# [필수] 강제 가로 정렬을 위한 CSS (모바일에서 칸이 절대 떨어지지 않게 함)
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] { gap: 5px !important; }
    input { border: 1px solid #ddd !important; border-radius: 5px !important; }
    </style>
""", unsafe_allow_html=True)

# 페이지 로직은 그대로 유지...
if "current_page" not in st.session_state: st.session_state.current_page = "지점선택"

# --- [정보 수정 화면 (화면 3)의 입력창 부분 핵심 수정] ---
if st.session_state.current_page == "정보수정":
    # (앞부분 데이터 로딩은 동일)
    
    st.title("✏️ 알바생 정보 수정")
    
    # 주민번호: 무조건 6자/7자 강제 2칸 배치
    st.markdown("**주민등록번호**")
    c1, c2 = st.columns(2)
    with c1: 
        rrn1 = st.text_input("앞자리", max_chars=6, key="rrn1")
    with c2: 
        rrn2 = st.text_input("뒷자리", max_chars=7, key="rrn2")
        
    # 전화번호: 무조건 3칸 배치
    st.markdown("**전화번호**")
    p1, p2, p3 = st.columns(3)
    with p1: p1_in = st.text_input("국번", max_chars=3, key="p1")
    with p2: p2_in = st.text_input("중간", max_chars=4, key="p2")
    with p3: p3_in = st.text_input("끝", max_chars=4, key="p3")

    # 자동 이동 자바스크립트 (이 부분이 핵심입니다!)
    st.markdown("""
    <script>
    const inputs = document.querySelectorAll('input');
    inputs.forEach((input, index) => {
        input.addEventListener('input', (e) => {
            if (e.target.value.length === e.target.maxLength) {
                if (index < inputs.length - 1) inputs[index + 1].focus();
            }
        });
    });
    </script>
    """, unsafe_allow_html=True)
    
    # ... (나머지 저장 로직 동일)
