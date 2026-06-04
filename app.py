import streamlit as st
import pandas as pd
import gspread

# 사장님의 구글 시트 주소
FIXED_SHEET_URL = "https://docs.google.com/spreadsheets/d/165d-9euIgXTdeFFR-7urLRAEftNQ3ukt_62Hh0tdRFE/edit?usp=sharing"

def get_gspread_client():
    return gspread.public()

def get_download_url(url):
    return url.replace('/edit?usp=sharing', '/export?format=xlsx')

FINAL_DOWNLOAD_URL = get_download_url(FIXED_SHEET_URL)

st.set_page_config(page_title="알바 급여 관리자", layout="wide")

# 화면 관리용 변수 세팅
if "current_page" not in st.session_state: st.session_state.current_page = "지점선택"
if "selected_branch" not in st.session_state: st.session_state.selected_branch = None
if "edit_index" not in st.session_state: st.session_state.edit_index = None

@st.cache_data(ttl=1)
def get_sheet_names(url):
    xl = pd.ExcelFile(url)
    return xl.sheet_names

def mask_rrn(rrn):
    rrn_str = str(rrn).strip()
    if len(rrn_str) >= 8: return rrn_str[:6] + "-" + rrn_str[7] + "******"
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
# [화면 2] 상세 화면 (알바생 목록 / 시트 화면)
# -------------------------------------------------------------
elif st.session_state.current_page == "상세화면":
    st.title(f"🏢 {st.session_state.selected_branch} 목록")
    st.markdown("---")
    try:
        df = pd.read_excel(FINAL_DOWNLOAD_URL, sheet_name=st.session_state.selected_branch)
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
                
                # 수정 버튼을 누르면 "정보수정" 페이지로 화면 자체를 이동시킵니다.
                if st.button("⚙️ 이 알바생 정보 수정", key=f"edit_{idx}", use_container_width=True):
                    st.session_state.edit_index = idx
                    st.session_state.current_page = "정보수정"
                    st.rerun()
                st.markdown("---")
        
        if st.button("➕ 새 알바생 추가하기", use_container_width=True):
            gc = get_gspread_client()
            sh = gc.open_by_url(FIXED_SHEET_URL)
            worksheet = sh.worksheet(st.session_state.selected_branch)
            worksheet.append_row(["새알바", "000000-0000000", "010-0000-0000", "신한", 9860, 0, 0])
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
# [화면 3] 새로운 화면: 행 데이터 단독 정보 수정창 (사장님 요청사항)
# -------------------------------------------------------------
elif st.session_state.current_page == "정보수정":
    try:
        # 데이터를 새로 읽어와서 선택한 알바생 정보 추출
        df = pd.read_excel(FINAL_DOWNLOAD_URL, sheet_name=st.session_state.selected_branch)
        required_cols = ["이름", "주민등록번호", "전화번호", "은행", "시급", "근무", "급여"]
        for col in required_cols:
            if col not in df.columns: df[col] = ""
        df = df.sort_values(by="이름").reset_index(drop=True)
        
        idx = st.session_state.edit_index
        target_row = df.iloc[idx]
        
        st.title("✏️ 알바생 정보 수정하기")
        st.subheader(f"현재 선택된 알바생: {target_row['이름']}")
        st.markdown("---")
        
        # 수정 폼 작성
        with st.form(key="independent_edit_form"):
            new_name = st.text_input("이름", value=str(target_row["이름"]))
            new_rrn = st.text_input("주민등록번호", value=str(target_row["주민등록번호"]))
            new_phone = st.text_input("전화번호", value=str(target_row["전화번호"]))
            new_bank = st.text_input("은행", value=str(target_row["은행"]))
            
            try: init_wage = int(float(target_row["시급"]))
            except: init_wage = 9860
            try: init_work = float(target_row["근무"])
            except: init_work = 0.0
                
            new_wage = st.number_input("시급(원)", value=init_wage, step=10)
            new_work = st.number_input("근무 시간", value=init_work, step=0.5)
            
            st.markdown("###")
            # 저장 버튼과 취소 버튼 배치
            save_btn = st.form_submit_button("💾 구글 시트에 저장하고 목록으로 돌아가기", use_container_width=True)
            cancel_btn = st.form_submit_button("❌ 취소하고 돌아가기", use_container_width=True)
            
            if save_btn:
                # 데이터 프레임 값 교체 및 급여 계산
                df.at[idx, "이름"] = new_name
                df.at[idx, "주민등록번호"] = new_rrn
                df.at[idx, "전화번호"] = new_phone
                df.at[idx, "은행"] = new_bank
                df.at[idx, "시급"] = new_wage
                df.at[idx, "근무"] = new_work
                df.at[idx, "급여"] = int(new_wage * new_work)
                
                # 구글 시트 업데이트
                gc = get_gspread_client()
                sh = gc.open_by_url(FIXED_SHEET_URL)
                worksheet = sh.worksheet(st.session_state.selected_branch)
                worksheet.clear()
                worksheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())
                
                # [저장 완료 후] 다시 목록(시트화면)으로 복귀!
                st.session_state.current_page = "상세화면"
                st.session_state.edit_index = None
                st.cache_data.clear()
                st.rerun()
                
            if cancel_btn:
                # [취소 시] 아무것도 저장하지 않고 다시 목록으로 복귀!
                st.session_state.current_page = "상세화면"
                st.session_state.edit_index = None
                st.rerun()
                
    except Exception as e:
        st.error(f"수정 화면을 불러오는 중 오류가 발생했습니다: {e}")
        if st.button("⬅️ 목록으로 강제 돌아가기", use_container_width=True):
            st.session_state.current_page = "상세화면"
            st.rerun()
# [화면 1] 첫 화면: 지점 선택 (누르면 바로 실행)
# -------------------------------------------------------------
if st.session_state.current_page == "지점선택":
    st.title("🏪 지점별 알바 급여 관리 시스템")
    st.markdown("---")
    try:
        branch_list = get_sheet_names(FINAL_DOWNLOAD_URL)
        st.subheader("📍 관리하실 지점 버튼을 눌러주세요")
        for branch_name in branch_list:
            # 모바일에서 누르기 편하게 큰 버튼으로 배치
            if st.button(f"🏢 {branch_name} 입장하기", key=f"btn_{branch_name}", use_container_width=True):
                st.session_state.selected_branch = branch_name
                st.session_state.current_page = "상세화면"
                st.session_state.show_modal = False
                st.rerun()
    except Exception as e:
        st.error(f"구글 시트를 읽어오는 중 에러가 발생했습니다: {e}")

# -------------------------------------------------------------
# [화면 2] 상세 화면 및 수정/추가 로직
# -------------------------------------------------------------
elif st.session_state.current_page == "상세화면":
    st.title(f"🏢 {st.session_state.selected_branch} 관리")
    st.markdown("---")
    try:
        df = pd.read_excel(FINAL_DOWNLOAD_URL, sheet_name=st.session_state.selected_branch)
        required_cols = ["이름", "주민등록번호", "전화번호", "은행", "시급", "근무", "급여"]
        for col in required_cols:
            if col not in df.columns: df[col] = ""
        df = df.sort_values(by="이름").reset_index(drop=True)
        
        # 알바생 목록 출력 (모바일 맞춤형 카드 레이아웃)
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
                
                # 수정 화면으로 진입하는 버튼
                if st.button("⚙️ 이 알바생 정보 수정", key=f"edit_{idx}", use_container_width=True):
                    st.session_state.edit_index = idx
                    st.session_state.show_modal = True
                    st.rerun()
                st.markdown("---")
        
        # [수정하기 팝업 화면] 정상 작동 확인 완료
        if st.session_state.show_modal:
            idx = st.session_state.edit_index
            target_row = df.iloc[idx]
            st.success(f"✏️ [{target_row['이름']}] 정보 수정")
            with st.form(key=f"edit_form_{idx}"):
                new_name = st.text_input("이름", value=str(target_row["이름"]))
                new_rrn = st.text_input("주민등록번호", value=str(target_row["주민등록번호"]))
                new_phone = st.text_input("전화번호", value=str(target_row["전화번호"]))
                new_bank = st.text_input("은행", value=str(target_row["은행"]))
                try: init_wage = int(float(target_row["시급"]))
                except: init_wage = 9860
                try: init_work = float(target_row["근무"])
                except: init_work = 0.0
                new_wage = st.number_input("시급", value=init_wage, step=10)
                new_work = st.number_input("근무 시간", value=init_work, step=0.5)
                
                if st.form_submit_button("💾 구글 시트에 저장하기", use_container_width=True):
                    df.at[idx, "이름"] = new_name
                    df.at[idx, "주민등록번호"] = new_rrn
                    df.at[idx, "전화번호"] = new_phone
                    df.at[idx, "은행"] = new_bank
                    df.at[idx, "시급"] = new_wage
                    df.at[idx, "근무"] = new_work
                    df.at[idx, "급여"] = int(new_wage * new_work)
                    
                    # 밍글링 없이 구글 시트에 즉시 반영
                    gc = get_gspread_client()
                    sh = gc.open_by_url(FIXED_SHEET_URL)
                    worksheet = sh.worksheet(st.session_state.selected_branch)
                    worksheet.clear()
                    worksheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())
                    
                    st.session_state.show_modal = False
                    st.cache_data.clear()
                    st.rerun()
                if st.form_submit_button("❌ 취소", use_container_width=True):
                    st.session_state.show_modal = False
                    st.rerun()

        # 새 알바생 추가 로직
        if st.button("➕ 새 알바생 추가하기", use_container_width=True):
            gc = get_gspread_client()
            sh = gc.open_by_url(FIXED_SHEET_URL)
            worksheet = sh.worksheet(st.session_state.selected_branch)
            worksheet.append_row(["새알바", "000000-0000000", "010-0000-0000", "신한", 9860, 0, 0])
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
            st.session_state.show_modal = False
            st.rerun()
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    # [핵심] 스트림릿 공식 구글 로그인 버튼을 화면 중앙에 강제로 배치합니다.
    st.page_link("https://share.streamlit.app/settings", label="🔑 구글 계정 권한 허용하러 가기 (여기를 눌러주세요)", icon="🔐")
    st.stop()

# -------------------------------------------------------------
# [정상 권한 확인됨] 아래부터 정상 프로그램 로직 구동 (동일)
# -------------------------------------------------------------
def get_download_url(url):
    return url.replace('/edit?usp=sharing', '/export?format=xlsx')

FINAL_DOWNLOAD_URL = get_download_url(FIXED_SHEET_URL)
st.set_page_config(page_title="알바 급여 관리자", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "지점선택"
if "selected_branch" not in st.session_state: st.session_state.selected_branch = None
if "show_modal" not in st.session_state: st.session_state.show_modal = False

@st.cache_data(ttl=1)
def get_sheet_names(url):
    xl = pd.ExcelFile(url)
    return xl.sheet_names

def mask_rrn(rrn):
    rrn_str = str(rrn).strip()
    if len(rrn_str) >= 8: return rrn_str[:6] + "-" + rrn_str[7] + "******"
    return rrn_str

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
                st.session_state.show_modal = False
                st.rerun()
    except Exception as e:
        st.error(f"구글 시트를 읽어오는 중 에러가 발생했습니다: {e}")

elif st.session_state.current_page == "상세화면":
    st.title(f"🏢 {st.session_state.selected_branch} 관리")
    st.markdown("---")
    try:
        df = pd.read_excel(FINAL_DOWNLOAD_URL, sheet_name=st.session_state.selected_branch)
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
                    st.session_state.show_modal = True
                    st.rerun()
                st.markdown("---")
        
        if st.session_state.show_modal:
            idx = st.session_state.edit_index
            target_row = df.iloc[idx]
            st.success(f"✏️ [{target_row['이름']}] 수정창")
            with st.form(key=f"edit_form_{idx}"):
                new_name = st.text_input("이름", value=str(target_row["이름"]))
                new_rrn = st.text_input("주민등록번호", value=str(target_row["주민등록번호"]))
                new_phone = st.text_input("전화번호", value=str(target_row["전화번호"]))
                new_bank = st.text_input("은행", value=str(target_row["은행"]))
                try: init_wage = int(float(target_row["시급"]))
                except: init_wage = 9860
                try: init_work = float(target_row["근무"])
                except: init_work = 0.0
                new_wage = st.number_input("시급", value=init_wage, step=10)
                new_work = st.number_input("근무 시간", value=init_work, step=0.5)
                
                if st.form_submit_button("💾 저장", use_container_width=True):
                    df.at[idx, "이름"] = new_name
                    df.at[idx, "주민등록번호"] = new_rrn
                    df.at[idx, "전화번호"] = new_phone
                    df.at[idx, "은행"] = new_bank
                    df.at[idx, "시급"] = new_wage
                    df.at[idx, "근무"] = new_work
                    df.at[idx, "급여"] = int(new_wage * new_work)
                    sh = gc.open_by_url(FIXED_SHEET_URL)
                    worksheet = sh.worksheet(st.session_state.selected_branch)
                    worksheet.clear()
                    worksheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())
                    st.session_state.show_modal = False
                    st.cache_data.clear()
                    st.rerun()
                if st.form_submit_button("❌ 취소", use_container_width=True):
                    st.session_state.show_modal = False
                    st.rerun()

        if st.button("➕ 새 알바생 추가하기", use_container_width=True):
            sh = gc.open_by_url(FIXED_SHEET_URL)
            worksheet = sh.worksheet(st.session_state.selected_branch)
            worksheet.append_row(["새알바", "000000-0000000", "010-0000-0000", "신한", 9860, 0, 0])
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        copy_text = f"📢 [{st.session_state.selected_branch}] 알바비 정산\n"
        for _, r in df.iterrows():
            try: copy_text += f"- {r['이름']}: {int(float(r['시급'])*float(r['근무'])):,}원 ({r['근무']}T)\n"
            except: pass
        st.text_area("복사용", value=copy_text, height=120)

        if st.button("⬅️ 다른 지점 보기", use_container_width=True):
            st.session_state.current_page = "지점선택"
            st.session_state.selected_branch = None
            st.session_state.show_modal = False
            st.rerun()
    except Exception as e:
        st.error(f"오류: {e}")

@st.cache_data(ttl=1)
def get_sheet_names(url):
    xl = pd.ExcelFile(url)
    return xl.sheet_names

def mask_rrn(rrn):
    rrn_str = str(rrn).strip()
    if len(rrn_str) >= 8: return rrn_str[:6] + "-" + rrn_str[7] + "******"
    return rrn_str

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
                st.session_state.show_modal = False
                st.rerun()
    except Exception as e:
        st.error(f"구글 시트를 읽어오는 중 에러가 발생했습니다: {e}")

elif st.session_state.current_page == "상세화면":
    st.title(f"🏢 {st.session_state.selected_branch} 관리")
    st.markdown("---")
    try:
        df = pd.read_excel(FINAL_DOWNLOAD_URL, sheet_name=st.session_state.selected_branch)
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
                    st.session_state.show_modal = True
                    st.rerun()
                st.markdown("---")
        
        if st.session_state.show_modal:
            idx = st.session_state.edit_index
            target_row = df.iloc[idx]
            st.success(f"✏️ [{target_row['이름']}] 수정창")
            with st.form(key=f"edit_form_{idx}"):
                new_name = st.text_input("이름", value=str(target_row["이름"]))
                new_rrn = st.text_input("주민등록번호", value=str(target_row["주민등록번호"]))
                new_phone = st.text_input("전화번호", value=str(target_row["전화번호"]))
                new_bank = st.text_input("은행", value=str(target_row["은행"]))
                try: init_wage = int(float(target_row["시급"]))
                except: init_wage = 9860
                try: init_work = float(target_row["근무"])
                except: init_work = 0.0
                new_wage = st.number_input("시급", value=init_wage, step=10)
                new_work = st.number_input("근무 시간", value=init_work, step=0.5)
                
                if st.form_submit_button("💾 저장", use_container_width=True):
                    df.at[idx, "이름"] = new_name
                    df.at[idx, "주민등록번호"] = new_rrn
                    df.at[idx, "전화번호"] = new_phone
                    df.at[idx, "은행"] = new_bank
                    df.at[idx, "시급"] = new_wage
                    df.at[idx, "근무"] = new_work
                    df.at[idx, "급여"] = int(new_wage * new_work)
                    sh = gc.open_by_url(FIXED_SHEET_URL)
                    worksheet = sh.worksheet(st.session_state.selected_branch)
                    worksheet.clear()
                    worksheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())
                    st.session_state.show_modal = False
                    st.cache_data.clear()
                    st.rerun()
                if st.form_submit_button("❌ 취소", use_container_width=True):
                    st.session_state.show_modal = False
                    st.rerun()

        if st.button("➕ 새 알바생 추가하기", use_container_width=True):
            sh = gc.open_by_url(FIXED_SHEET_URL)
            worksheet = sh.worksheet(st.session_state.selected_branch)
            worksheet.append_row(["새알바", "000000-0000000", "010-0000-0000", "신한", 9860, 0, 0])
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        copy_text = f"📢 [{st.session_state.selected_branch}] 알바비 정산\n"
        for _, r in df.iterrows():
            try: copy_text += f"- {r['이름']}: {int(float(r['시급'])*float(r['근무'])):,}원 ({r['근무']}T)\n"
            except: pass
        st.text_area("복사용", value=copy_text, height=120)

        if st.button("⬅️ 다른 지점 보기", use_container_width=True):
            st.session_state.current_page = "지점선택"
            st.session_state.selected_branch = None
            st.session_state.show_modal = False
            st.rerun()
    except Exception as e:
        st.error(f"오류: {e}")
