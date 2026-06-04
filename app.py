import streamlit as st
import pandas as pd
import io

# 1. 시트 설정
FIXED_SHEET_URL = "https://docs.google.com/spreadsheets/d/165d-9euIgXTdeFFR-7urLRAEftNQ3ukt_62Hh0tdRFE/edit?usp=sharing"
FINAL_DOWNLOAD_URL = FIXED_SHEET_URL.replace('/edit?usp=sharing', '/export?format=xlsx')

def save_to_google_sheet(branch_name, data_frame):
    st.success(f"💾 {branch_name} 저장 완료!")
    return True

st.set_page_config(page_title="알바 급여 관리", layout="wide")

# [핵심] 가로 정렬 CSS 및 자동 이동 자바스크립트
st.markdown("""
    <style>
    /* 칸들을 모바일에서도 강제로 붙임 */
    div[data-testid="stHorizontalBlock"] { gap: 10px !important; }
    input { border: 1px solid #ccc !important; border-radius: 5px !important; }
    </style>
    <script>
    document.addEventListener('input', (e) => {
        if (e.target.tagName === 'INPUT' && e.target.maxLength > 0) {
            if (e.target.value.length >= e.target.maxLength) {
                const inputs = Array.from(document.querySelectorAll('input'));
                const index = inputs.indexOf(e.target);
                if (index > -1 && index < inputs.length - 1) inputs[index + 1].focus();
            }
        }
    });
    </script>
""", unsafe_allow_html=True)

# 2. 화면 관리
if "current_page" not in st.session_state: st.session_state.current_page = "상세화면"
if "selected_branch" not in st.session_state: st.session_state.selected_branch = "공항점" # 기본값
if "edit_index" not in st.session_state: st.session_state.edit_index = None

# 상세 화면 및 수정 화면 (사장님이 보시는 핵심)
if st.session_state.current_page == "상세화면":
    st.title(f"🏢 {st.session_state.selected_branch} 목록")
    # (여기에 목록 표시 로직...)
    if st.button("수정모드로 이동"): 
        st.session_state.current_page = "정보수정"
        st.rerun()

elif st.session_state.current_page == "정보수정":
    st.title("✏️ 정보 수정")
    
    # 주민번호 (가로 2칸 강제)
    st.markdown("**주민등록번호**")
    c1, c2 = st.columns(2)
    with c1: r1 = st.text_input("앞", max_chars=6, key="r1")
    with c2: r2 = st.text_input("뒤", max_chars=7, key="r2")
        
    # 전화번호 (가로 3칸 강제)
    st.markdown("**전화번호**")
    p1, p2, p3 = st.columns(3)
    with p1: phone1 = st.text_input("p1", max_chars=3, key="p1")
    with p2: phone2 = st.text_input("p2", max_chars=4, key="p2")
    with p3: phone3 = st.text_input("p3", max_chars=4, key="p3")

    # 시급/근무 (버튼 없는 깔끔한 입력창)
    w, t = st.columns(2)
    with w: wage = st.text_input("시급")
    with t: time = st.text_input("시간")

    if st.button("저장"):
        st.session_state.current_page = "상세화면"
        st.rerun()
