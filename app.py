import streamlit as st
import pandas as pd
import io

# 1. 설정 및 데이터 로딩 함수
FIXED_SHEET_URL = "https://docs.google.com/spreadsheets/d/165d-9euIgXTdeFFR-7urLRAEftNQ3ukt_62Hh0tdRFE/edit?usp=sharing"
FINAL_DOWNLOAD_URL = FIXED_SHEET_URL.replace('/edit?usp=sharing', '/export?format=xlsx')

@st.cache_data(ttl=1)
def load_data(url, sheet):
    return pd.read_excel(url, sheet_name=sheet)

def save_to_google_sheet(branch_name, data_frame):
    st.success("데이터가 반영되었습니다!")
    return True

# 2. 강제 가로 정렬 CSS (모바일에서 칸 떨어지지 않게 함)
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] { gap: 5px !important; }
    </style>
""", unsafe_allow_html=True)

# 3. 화면 상태 관리
if "current_page" not in st.session_state: st.session_state.current_page = "지점선택"
if "selected_branch" not in st.session_state: st.session_state.selected_branch = None
if "edit_index" not in st.session_state: st.session_state.edit_index = None

# 4. 각 화면 로직
if st.session_state.current_page == "지점선택":
    st.title("🏪 지점 선택")
    branch_list = pd.ExcelFile(FINAL_DOWNLOAD_URL).sheet_names
    for b in branch_list:
        if st.button(f"{b} 입장"):
            st.session_state.selected_branch = b
            st.session_state.current_page = "상세화면"
            st.rerun()

elif st.session_state.current_page == "상세화면":
    st.title(f"{st.session_state.selected_branch} 목록")
    df = load_data(FINAL_DOWNLOAD_URL, st.session_state.selected_branch)
    for idx, row in df.iterrows():
        st.write(f"👤 {row['이름']}")
        if st.button("수정", key=f"edit_{idx}"):
            st.session_state.edit_index = idx
            st.session_state.current_page = "정보수정"
            st.rerun()

elif st.session_state.current_page == "정보수정":
    df = load_data(FINAL_DOWNLOAD_URL, st.session_state.selected_branch)
    row = df.iloc[st.session_state.edit_index]
    
    st.title("✏️ 정보 수정")
    # 이름
    name = st.text_input("이름", value=row["이름"])
    
    # 주민번호 (가로 2칸 강제)
    st.markdown("**주민번호**")
    c1, c2 = st.columns(2)
    with c1: r1 = st.text_input("앞", value=str(row["주민등록번호"]).split("-")[0] if "-" in str(row["주민등록번호"]) else "", max_chars=6)
    with c2: r2 = st.text_input("뒤", value=str(row["주민등록번호"]).split("-")[1] if "-" in str(row["주민등록번호"]) else "", max_chars=7)
    
    # 전화번호 (가로 3칸 강제)
    st.markdown("**전화번호**")
    p1, p2, p3 = st.columns(3)
    with p1: ph1 = st.text_input("국번", max_chars=3)
    with p2: ph2 = st.text_input("중간", max_chars=4)
    with p3: ph3 = st.text_input("끝", max_chars=4)

    # 시급/근무
    w, t = st.columns(2)
    with w: wage = st.text_input("시급", value=row["시급"])
    with t: time = st.text_input("시간", value=row["근무"])

    if st.button("저장"):
        # 여기서 df 업데이트 후 저장 로직 수행
        st.session_state.current_page = "상세화면"
        st.rerun()
    if st.button("취소"):
        st.session_state.current_page = "상세화면"
        st.rerun()
