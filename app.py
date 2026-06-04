import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 사장님의 구글 시트 주소
FIXED_SHEET_URL = "https://docs.google.com/spreadsheets/d/165d-9euIgXTdeFFR-7urLRAEftNQ3ukt_62Hh0tdRFE/edit?usp=sharing"

st.set_page_config(page_title="알바 급여 관리자", layout="wide")

# 화면 관리용 핵심 변수 세팅
if "current_page" not in st.session_state: st.session_state.current_page = "지점선택"
if "selected_branch" not in st.session_state: st.session_state.selected_branch = None
if "edit_index" not in st.session_state: st.session_state.edit_index = None

# [가장 안정적인 대기업 직통 연결 방식]
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=1)
def load_branch_data(branch_name):
    # 구글 시트에서 해당 지점 데이터를 깔끔하게 긁어옵니다.
    return conn.read(spreadsheet=FIXED_SHEET_URL, sheet=branch_name)

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
        # 엑셀 파일 열어서 시트 이름만 추출
        url_xl = FIXED_SHEET_URL.replace('/edit?usp=sharing', '/export?format=xlsx')
        xl = pd.ExcelFile(url_xl)
        branch_list = xl.sheet_names
        
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
        raw_df = load_branch_data(st.session_state.selected_branch)
        df = pd.DataFrame(raw_df)
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
            # 새 행 추가 후 구글 시트 업데이트
            new_row = pd.DataFrame([["새알바", "000000-0000000", "010-0000-0000", "신한", 9860, 0, 0]], columns=df.columns)
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=FIXED_SHEET_URL, sheet=st.session_state.selected_branch, data=updated_df)
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
# [화면 3] 정보 수정 화면 (가로 한 줄 배치 완료)
# -------------------------------------------------------------
elif st.session_state.current_page == "정보수정":
    try:
        raw_df = load_branch_data(st.session_state.selected_branch)
        df = pd.DataFrame(raw_df)
        df = df.sort_values(by="이름").reset_index(drop=True)
        idx = st.session_state.edit_index
        target_row = df.iloc[idx]
        
        st.title("✏️ 알바생 정보 수정하기")
        st.markdown("---")
        
        # 글자 쪼개기 파싱 로직
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
        if not b_num and b_name and any(c.isdigit() for c in b_name):
            import re
            nums = re.findall(r'\d+', b_name)
            if nums:
                b_num = nums[0]
                b_name = b_name.replace(b_num, "").strip()

        # 1. 이름 입력창
        new_name = st.text_input("이름", value=None, placeholder=str(target_row["이름"]))
        if not new_name: new_name = str(target_row["이름"])
        
        # 2. 주민등록번호 (가로 2칸 나란히 배치, 불필요한 라벨 삭제)
        st.markdown("**주민등록번호**")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            new_rrn1 = st.text_input("주민1", value=None, placeholder=rrn1 if rrn1 else "앞 6자리", max_chars=6, label_visibility="collapsed")
            if not new_rrn1: new_rrn1 = rrn1
        with col_r2:
            new_rrn2 = st.text_input("주민2", value=None, placeholder=rrn2 if rrn2 else "뒤 7자리", max_chars=7, label_visibility="collapsed")
            if not new_rrn2: new_rrn2 = rrn2

        # 3. 전화번호 (가로 3칸 나란히 배치, 불필요한 라벨 삭제)
        st.markdown("**전화번호**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            new_p1 = st.text_input("폰1", value=None, placeholder=p1 if p1 else "010", label_visibility="collapsed")
            if not new_p1: new_p1 = p1
        with col_p2:
            new_p2 = st.text_input("폰2", value=None, placeholder=p2 if p2 else "0000", label_visibility="collapsed")
            if not new_p2: new_p2 = p2
        with col_p3:
            new_p3 = st.text_input("폰3", value=None, placeholder=p3 if p3 else "0000", label_visibility="collapsed")
            if not new_p3: new_p3 = p3

        # 4. 계좌 정보 (가로 2칸 나란히 배치, 불필요한 라벨 삭제)
        st.markdown("**계좌 정보 (은행명 / 계좌번호)**")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            new_b_name = st.text_input("은행", value=None, placeholder=b_name if b_name else "은행명", label_visibility="collapsed")
            if not new_b_name: new_b_name = b_name
        with col_b2:
            new_b_num = st.text_input("계좌", value=None, placeholder=b_num if b_num else "계좌번호 (숫자만)", label_visibility="collapsed")
            if not new_b_num: new_b_num = b_num

        try: init_wage = int(float(target_row["시급"]))
        except: init_wage = 9860
        try: init_work = float(target_row["근무"])
        except: init_work = 0.0
            
        new_wage = st.number_input("시급(원)", value=init_wage, step=10)
        new_work = st.number_input("근무 시간", value=init_work, step=0.5)
        
        st.markdown("###")
        
        # 버튼 액션 로직
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
            
            # [대기업 안심 커넥션]으로 구글 시트 원본 덮어쓰기 완료
            conn.update(spreadsheet=FIXED_SHEET_URL, sheet=st.session_state.selected_branch, data=df)
            
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
