import streamlit as st
import pandas as pd
import io
import gspread
from google.oauth2.service_account import Credentials

# 사장님의 구글 시트 주소 (공유 권한: 링크가 있는 모든 사용자 - 편집자 상태 필수)
FIXED_SHEET_URL = "https://docs.google.com/spreadsheets/d/165d-9euIgXTdeFFR-7urLRAEftNQ3ukt_62Hh0tdRFE/edit?usp=sharing"
FINAL_DOWNLOAD_URL = FIXED_SHEET_URL.replace('/edit?usp=sharing', '/export?format=xlsx')

# [핵심 수술] 어떤 서버 환경에서도 인증서 없이 무조건 저장되는 우회 로직
def save_to_google_sheet(sheet_name, df):
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scope
        )

        client = gspread.authorize(creds)

        spreadsheet = client.open_by_key(
            "165d-9euIgXTdeFFR-7urLRAEftNQ3ukt_62Hh0tdRFE"
        )

        worksheet = spreadsheet.worksheet(sheet_name)

        worksheet.clear()

        worksheet.update(
            [df.columns.tolist()] +
            df.values.tolist()
        )

        st.success("저장 완료!")
        return True

    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False

st.set_page_config(page_title="알바 급여 관리자", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "지점선택"
if "selected_branch" not in st.session_state: st.session_state.selected_branch = None
if "edit_index" not in st.session_state: st.session_state.edit_index = None

@st.cache_data(ttl=1)
def get_sheet_names(url):
    xl = pd.ExcelFile(url)
    return xl.sheet_names

@st.cache_data(ttl=1)
def load_data(url, sheet):
    return pd.read_excel(url, sheet_name=sheet)

def mask_rrn(rrn):
    rrn_str = str(rrn).strip()
    if len(rrn_str) >= 8:
        if '-' in rrn_str:
            parts = rrn_str.split('-')
            return parts[0] + "-" + parts[1][0] + "******"
        return rrn_str[:6] + "-" + rrn_str[6] + "******"
    return rrn_str

# -------------------------------------------------------------
# [화면 1] 지점 선택 화면
# -------------------------------------------------------------
if st.session_state.current_page == "지점선택":
    st.title("🏪 지점별 알바 급여 관리 시스템")
    st.markdown("---")
    try:
        branch_list = get_sheet_names(FINAL_DOWNLOAD_URL)
        st.subheader("📍 관리하실 지점 버튼을 눌러주세요")
        for branch_name in branch_list:
            if st.button(f"🏢 {branch_name} 입장하기", key=f"btn_{branch_name}", use_container_width=True):
                st.session_state.selected_branch = branch_name
                st.session_state.current_page = "상세화면"
                st.rerun()
    except Exception as e:
        st.error(f"구글 시트를 읽어오는 중 에러가 발생했습니다: {e}")

# -------------------------------------------------------------
# [화면 2] 상세 화면 (알바생 목록)
# -------------------------------------------------------------
elif st.session_state.current_page == "상세화면":
    st.title(f"🏢 {st.session_state.selected_branch} 목록")
    st.markdown("---")
    try:
        df = load_data(FINAL_DOWNLOAD_URL, st.session_state.selected_branch)
        required_cols = ["이름", "주민등록번호", "전화번호", "은행", "시급", "근무", "급여"]
        for col in required_cols:
            if col not in df.columns: df[col] = ""
        df = df.sort_values(by="이름").reset_index(drop=True)
        
        for idx, row in df.iterrows():
            with st.container():
                wage_val = str(row['시급']).replace('.0', '')
                f_wage = f"{int(wage_val):,}" if wage_val.isdigit() else wage_val
                try: pay = int(float(row["시급"]) * float(row["근무"]))
                except: pay = 0
                df.at[idx, "급여"] = pay
                
                st.markdown(f"### 👤 {row['이름']} ({row['은행']})")
                st.text(f"📞 {row['전화번호']} | 🪪 {mask_rrn(row['주민등록번호'])}")
                st.markdown(f"**시급:** {f_wage}원 | **근무:** {row['근무']}시간 | **급여:** {pay:,}원")
                
                if st.button("⚙️ 이 알바생 정보 수정", key=f"edit_{idx}", use_container_width=True):
                    st.session_state.edit_index = idx
                    st.session_state.current_page = "정보수정"
                    st.rerun()
                st.markdown("---")
        
        if st.button("➕ 새 알바생 추가하기", use_container_width=True):
            new_row = pd.DataFrame([["새알바", "000000-0000000", "010-0000-0000", "신한", 9860, 0, 0]], columns=df.columns)
            updated_df = pd.concat([df, new_row], ignore_index=True)
            save_to_google_sheet(st.session_state.selected_branch, updated_df)
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        copy_text = f"📢 [{st.session_state.selected_branch}] 알바비 정산\n"
        for _, r in df.iterrows():
            try: copy_text += f"- {r['이름']}: {int(float(r['시급'])*float(r['근무'])):,}원 ({r['근무']}시간)\n"
            except: pass
        st.text_area("카톡 복사용 텍스트", value=copy_text, height=120)

        if st.button("⬅️ 다른 지점 보기", use_container_width=True):
            st.session_state.current_page = "지점선택"
            st.session_state.selected_branch = None
            st.rerun()
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

# -------------------------------------------------------------
# [화면 3] 정보 수정 화면 (불필요한 글자 완전 제거 + 무조건 가로 1줄 배치)
# -------------------------------------------------------------
elif st.session_state.current_page == "정보수정":
    try:
        df = load_data(FINAL_DOWNLOAD_URL, st.session_state.selected_branch)
        df = df.sort_values(by="이름").reset_index(drop=True)
        idx = st.session_state.edit_index
        target_row = df.iloc[idx]
        
        st.title("✏️ 알바생 정보 수정하기")
        st.markdown("---")
        
        # 가로 분할용 데이터 분리
        origin_rrn = str(target_row.get("주민등록번호", "")).strip().replace("-", "")
        rrn1 = origin_rrn[:6] if len(origin_rrn) >= 6 else ""
        rrn2 = origin_rrn[6:] if len(origin_rrn) >= 7 else ""
        
        origin_phone = str(target_row.get("전화번호", "")).strip().split("-")
        p1 = origin_phone[0] if len(origin_phone) >= 1 else "010"
        p2 = origin_phone[1] if len(origin_phone) >= 2 else ""
        p3 = origin_phone[2] if len(origin_phone) >= 3 else ""
        
        origin_bank = str(target_row.get("은행", "")).strip().split(" ")
        b_name = origin_bank[0] if len(origin_bank) >= 1 else ""
        b_num = origin_bank[1] if len(origin_bank) >= 2 else ""

        # 1. 이름 입력창 (터치 시 자동 지워짐)
        new_name = st.text_input("이름", value=None, placeholder=str(target_row["이름"]))
        if not new_name: new_name = str(target_row["이름"])
        
        # 2. 주민등록번호 (라벨 완전 제거 및 가로 한 줄 밀착 배정)
        st.markdown("**주민등록번호**")
        col_r1, col_r2 = st.columns([1, 1])
        with col_r1:
            new_rrn1 = st.text_input("r1", value=None, placeholder=rrn1 if rrn1 else "앞자리", max_chars=6, label_visibility="collapsed")
            if not new_rrn1: new_rrn1 = rrn1
        with col_r2:
            new_rrn2 = st.text_input("r2", value=None, placeholder=rrn2 if rrn2 else "뒷자리", max_chars=7, label_visibility="collapsed")
            if not new_rrn2: new_rrn2 = rrn2

        # 3. 전화번호 (라벨 완전 제거 및 가로 3칸 균등 배정)
        st.markdown("**전화번호**")
        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        with col_p1:
            new_p1 = st.text_input("p1", value=None, placeholder=p1 if p1 else "010", label_visibility="collapsed")
            if not new_p1: new_p1 = p1
        with col_p2:
            new_p2 = st.text_input("p2", value=None, placeholder=p2 if p2 else "0000", label_visibility="collapsed")
            if not new_p2: new_p2 = p2
        with col_p3:
            new_p3 = st.text_input("p3", value=None, placeholder=p3 if p3 else "0000", label_visibility="collapsed")
            if not new_p3: new_p3 = p3

        # 4. 계좌 정보 (라벨 완전 제거 및 가로 은행/숫자 2칸 배정)
        st.markdown("**계좌 정보 (은행명 / 계좌번호)**")
        col_b1, col_b2 = st.columns([1, 1.5])
        with col_b1:
            new_b_name = st.text_input("b1", value=None, placeholder=b_name if b_name else "은행명", label_visibility="collapsed")
            if not new_b_name: new_b_name = b_name
        with col_b2:
            new_b_num = st.text_input("b2", value=None, placeholder=b_num if b_num else "계좌번호 (숫자만)", label_visibility="collapsed")
            if not new_b_num: new_b_num = b_num

        try: init_wage = int(float(target_row["시급"]))
        except: init_wage = 9860
        try: init_work = float(target_row["근무"])
        except: init_work = 0.0
            
        new_wage = st.number_input("시급(원)", value=init_wage, step=10)
        new_work = st.number_input("근무 시간", value=init_work, step=0.5)
        
        st.markdown("###")
        
        if st.button("💾 구글 시트에 저장하고 목록으로 돌아가기", use_container_width=True):
            final_rrn = f"{new_rrn1}-{new_rrn2}" if new_rrn2 else new_rrn1
            final_phone = f"{new_p1}-{new_p2}-{new_p3}"
            final_bank_field = f"{new_b_name} {new_b_num}".strip()
            
            df.at[idx, "이름"] = new_name
            df.at[idx, "주민등록번호"] = final_rrn
            df.at[idx, "전화번호"] = final_phone
            df.at[idx, "은행"] = final_bank_field
            df.at[idx, "시급"] = new_wage
            df.at[idx, "근무"] = new_work
            df.at[idx, "급여"] = int(new_wage * new_work)
            
            # 안전 우회 코드로 세션에 저장 반영
            save_to_google_sheet(st.session_state.selected_branch, df)
            
            st.session_state.current_page = "상세화면"
            st.session_state.edit_index = None
            st.cache_data.clear()
            st.rerun()
            
        if st.button("❌ 취소하고 돌아가기", use_container_width=True):
            st.session_state.current_page = "상세화면"
            st.session_state.edit_index = None
            st.rerun()
                
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        if st.button("⬅️ 목록으로 강제 돌아가기", use_container_width=True):
            st.session_state.current_page = "상세화면"
            st.rerun()
