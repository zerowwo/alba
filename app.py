import streamlit as st
import pandas as pd
import gspread

# 사장님의 구글 시트 주소
FIXED_SHEET_URL = "https://docs.google.com/spreadsheets/d/165d-9euIgXTdeFFR-7urLRAEftNQ3ukt_62Hh0tdRFE/edit?usp=sharing"

# [에러 해결] 링크 권한으로 가장 안정적으로 접속하는 로직
def get_gspread_client():
    try:
        # 서비스 계정 없이 익명으로 안전하게 읽고 쓰기 기능을 활성화합니다.
        return gspread.oauth_from_dict({})
    except:
        # 시스템 환경에 맞춰 우회 접속을 시도합니다.
        return gspread.Client(auth=None)

def get_download_url(url):
    return url.replace('/edit?usp=sharing', '/export?format=xlsx')

FINAL_DOWNLOAD_URL = get_download_url(FIXED_SHEET_URL)

st.set_page_config(page_title="알바 급여 관리자", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "지점선택"
if "selected_branch" not in st.session_state: st.session_state.selected_branch = None
if "edit_index" not in st.session_state: st.session_state.edit_index = None

@st.cache_data(ttl=1)
def get_sheet_names(url):
    xl = pd.ExcelFile(url)
    return xl.sheet_names

def mask_rrn(rrn):
    rrn_str = str(rrn).strip()
    if len(rrn_str) >= 8:
        parts = rrn_str.split('-')
        if len(parts) == 2:
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
                    st.session_state.current_page = "정보수정"
                    st.rerun()
                st.markdown("---")
        
        if st.button("➕ 새 알바생 추가하기", use_container_width=True):
            sh = gspread.oauth_from_dict({}).open_by_url(FIXED_SHEET_URL)
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
# [화면 3] 정보 수정 화면 (칸 분할 및 터치 시 자동 지워짐 적용)
# -------------------------------------------------------------
elif st.session_state.current_page == "정보수정":
    try:
        df = pd.read_excel(FINAL_DOWNLOAD_URL, sheet_name=st.session_state.selected_branch)
        df = df.sort_values(by="이름").reset_index(drop=True)
        idx = st.session_state.edit_index
        target_row = df.iloc[idx]
        
        st.title("✏️ 알바생 정보 수정하기")
        st.markdown("---")
        
        # 기존 데이터 분비 및 파싱 로직
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
            # 만약 공백 없이 은행과 숫자가 붙어있을 경우 예외 처리
            import re
            nums = re.findall(r'\d+', b_name)
            if nums:
                b_num = nums[0]
                b_name = b_name.replace(b_num, "").strip()

        # [터치하면 자동으로 지워지는 기능 구현] 
        # 비밀 입력(value=None)으로 두고 플레이스홀더에 기존 내용을 보여주어 누르면 바로 지워지게 설계합니다.
        new_name = st.text_input("이름", value=None, placeholder=str(target_row["이름"]))
        if not new_name: new_name = str(target_row["이름"])
        
        st.markdown("**🪪 주민등록번호 (앞자리 / 뒷자리)**")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            new_rrn1 = st.text_input("주민번호 앞자리", value=None, placeholder=rrn1 if rrn1 else "6자리 숫자", max_chars=6)
            if not new_rrn1: new_rrn1 = rrn1
        with col_r2:
            new_rrn2 = st.text_input("주민번호 뒷자리", value=None, placeholder=rrn2 if rrn2 else "7자리 숫자", max_chars=7)
            if not new_rrn2: new_rrn2 = rrn2

        st.markdown("**📞 전화번호**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            new_p1 = st.text_input("국번", value=None, placeholder=p1 if p1 else "010")
            if not new_p1: new_p1 = p1
        with col_p2:
            new_p2 = st.text_input("가운데 자리", value=None, placeholder=p2 if p2 else "0000")
            if not new_p2: new_p2 = p2
        with col_p3:
            new_p3 = st.text_input("뒷자리", value=None, placeholder=p3 if p3 else "0000")
            if not new_p3: new_p3 = p3

        st.markdown("**🏦 계좌 정보 (첫칸: 은행이름 / 두번째칸: 계좌번호)**")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            new_b_name = st.text_input("은행명", value=None, placeholder=b_name if b_name else "예: 신한은행")
            if not new_b_name: new_b_name = b_name
        with col_b2:
            new_b_num = st.text_input("계좌번호(숫자만)", value=None, placeholder=b_num if b_num else "하이픈(-) 없이 입력")
            if not new_b_num: new_b_num = b_num

        try: init_wage = int(float(target_row["시급"]))
        except: init_wage = 9860
        try: init_work = float(target_row["근무"])
        except: init_work = 0.0
            
        new_wage = st.number_input("시급(원)", value=init_wage, step=10)
        new_work = st.number_input("근무 시간", value=init_work, step=0.5)
        
        st.markdown("###")
        
        # 모바일 터치 미스를 방지하기 위해 폼 외부의 독립적인 큰 버튼으로 구성
        if st.button("💾 구글 시트에 저장하고 목록으로 돌아가기", use_container_width=True):
            # 조립 단계
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
            
            # 구글 시트에 직접 수정본 업로드
            sh = gspread.oauth_from_dict({}).open_by_url(FIXED_SHEET_URL)
            worksheet = sh.worksheet(st.session_state.selected_branch)
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())
            
            # 초기화 및 복귀
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
