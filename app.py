import streamlit as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
import io
import os
import shutil

# --- 설정 ---
TEMPLATE_FILE = "template.pptx"
LOGO_DIR = "assets/logos"
ARTWORK_DIR = "assets/artworks"

# --- 초기화 함수 ---
def init_folders():
    for folder in [LOGO_DIR, ARTWORK_DIR]:
        if not os.path.exists(folder):
            os.makedirs(folder)

def get_files(folder_path):
    if not os.path.exists(folder_path):
        return []
    return [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

# --- 세션 상태 ---
if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# --- 기능 로직 (파일 처리) ---
def save_uploaded_file(uploaded_file, folder):
    file_path = os.path.join(folder, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

def delete_file(folder, filename):
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

def rename_file(folder, old_name, new_name):
    old_path = os.path.join(folder, old_name)
    ext = os.path.splitext(old_name)[1]
    if not new_name.endswith(ext): new_name += ext
    new_path = os.path.join(folder, new_name)
    if os.path.exists(new_path): return False, "중복된 이름입니다."
    os.rename(old_path, new_path)
    return True, "성공"

# --- 기능 로직 (PPT 생성) ---
def create_pptx(products):
    if os.path.exists(TEMPLATE_FILE):
        prs = Presentation(TEMPLATE_FILE)
    else:
        prs = Presentation()

    for data in products:
        try: slide_layout = prs.slide_layouts[1] 
        except: slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)

        # 텍스트
        textbox = slide.shapes.add_textbox(Inches(0.5), Inches(0.8), Inches(5), Inches(1))
        p = textbox.text_frame.paragraphs[0]
        p.text = f"{data['name']}\n{data['code']}"
        p.font.size = Pt(24)
        p.font.bold = True
        
        rrp_box = slide.shapes.add_textbox(Inches(7.5), Inches(0.8), Inches(2), Inches(0.5))
        rrp_box.text_frame.text = f"RRP : {data['rrp']}"
        rrp_box.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

        # 이미지
        if data['main_image']:
            slide.shapes.add_picture(data['main_image'], left=Inches(1.0), top=Inches(2.5), width=Inches(4.5))
        if data['logo'] and data['logo'] != "선택 없음":
            p_logo = os.path.join(LOGO_DIR, data['logo'])
            if os.path.exists(p_logo): slide.shapes.add_picture(p_logo, left=Inches(6.0), top=Inches(2.0), width=Inches(1.5))
        if data['artwork'] and data['artwork'] != "선택 없음":
            p_art = os.path.join(ARTWORK_DIR, data['artwork'])
            if os.path.exists(p_art): slide.shapes.add_picture(p_art, left=Inches(6.0), top=Inches(3.8), width=Inches(1.5))

        # 컬러웨이
        sx, sy, w, g = 6.0, 6.0, 1.2, 0.3
        for i, c in enumerate(data['colors']):
            cx = sx + (i * (w + g))
            if c['img']: slide.shapes.add_picture(c['img'], left=Inches(cx), top=Inches(sy), width=Inches(w))
            tb = slide.shapes.add_textbox(Inches(cx), Inches(sy + 1.3), Inches(w), Inches(0.4))
            p = tb.text_frame.paragraphs[0]
            p.text = c['name']
            p.font.size = Pt(9)
            p.alignment = PP_ALIGN.CENTER
            
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output

# =========================================================
# 🎨 CSS (Toss Admin Layout & Reset)
# =========================================================
st.set_page_config(page_title="BOSS Admin", layout="wide", initial_sidebar_state="expanded")
init_folders()

st.markdown("""
<style>
    /* 1. 폰트 및 기본 리셋 */
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
    
    * {
        font-family: 'Pretendard', sans-serif !important;
        box-sizing: border-box;
    }
    
    /* Streamlit 기본 패딩/마진 제거 (완전 초기화) */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }
    
    /* 상단 툴바/헤더/푸터 숨기기 */
    header[data-testid="stHeader"] { visibility: hidden; height: 0; }
    div[data-testid="stToolbar"] { visibility: hidden; height: 0; }
    footer { visibility: hidden; height: 0; }
    
    /* 배경색 (우측 메인 영역) */
    .stApp {
        background-color: #F2F4F6; /* 토스 배경 회색 */
    }

    /* 2. 사이드바 스타일 (좌측 메뉴) */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF; /* 사이드바 흰색 */
        border-right: 1px solid #E5E8EB;
        width: 260px !important;
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* 사이드바 내부 라디오 버튼 -> 메뉴처럼 보이게 커스텀 */
    div[data-testid="stRadio"] > label {
        display: none; /* 라벨 숨김 */
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 4px;
        border: none;
        transition: background 0.2s;
        cursor: pointer;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background-color: #F2F4F6;
    }
    /* 선택된 메뉴 스타일 */
    div[data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #E8F3FF !important; /* 연한 블루 */
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"] p {
        color: #3182F6 !important; /* 블루 텍스트 */
        font-weight: 700 !important;
    }
    div[data-testid="stRadio"] p {
        font-size: 15px;
        color: #4E5968;
        font-weight: 500;
    }

    /* 3. 콘텐츠 카드 스타일 (우측 영역) */
    .content-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 32px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
        margin-bottom: 20px;
        border: 1px solid #F2F4F6;
    }

    /* 4. 입력 필드 및 버튼 스타일 */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stFileUploader {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E8EB !important;
        border-radius: 8px !important;
        color: #333D4B !important;
        font-size: 14px !important;
    }
    div.stButton > button {
        background-color: #3182F6 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        font-size: 14px !important;
        width: 100%;
    }
    
    /* 5. 텍스트 스타일 */
    h1 { font-size: 24px !important; font-weight: 700 !important; color: #191F28 !important; margin-bottom: 8px !important; }
    h2 { font-size: 20px !important; font-weight: 700 !important; color: #333D4B !important; }
    h3 { font-size: 16px !important; font-weight: 600 !important; color: #333D4B !important; }
    p, span, label { color: #4E5968 !important; }
    
</style>
""", unsafe_allow_html=True)

# =========================================================
# 좌측 사이드바 (메뉴 영역)
# =========================================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Hugo_Boss_logo.svg/2560px-Hugo_Boss_logo.svg.png", width=100) # 로고 플레이스홀더
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    
    # 메뉴 선택 (라디오 버튼을 메뉴처럼 스타일링)
    menu = st.radio(
        "Navigation", 
        ["홈 (Dashboard)", "스펙 시트 제작 (Maker)", "자산 관리 (Assets)"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.caption("BOSS Admin v1.2")
    st.caption("Designed for Efficiency")

# =========================================================
# 우측 메인 콘텐츠 영역
# =========================================================

# 1. 홈 (대시보드)
if "홈" in menu:
    st.title("홈")
    st.markdown("안녕하세요, 관리자님. 오늘의 작업 현황입니다.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="content-card">
            <h3>생성된 시트</h3>
            <h2 style="color:#3182F6;">124건</h2>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="content-card">
            <h3>보유 로고</h3>
            <h2 style="color:#3182F6;">{len(get_files(LOGO_DIR))}개</h2>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="content-card">
            <h3>보유 아트워크</h3>
            <h2 style="color:#3182F6;">{len(get_files(ARTWORK_DIR))}개</h2>
        </div>
        """, unsafe_allow_html=True)

# 2. 스펙 시트 제작 (Maker)
elif "스펙" in menu:
    st.title("스펙 시트 제작")
    st.markdown("제품 정보를 입력하고 파워포인트 파일을 생성하세요.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 전체를 감싸는 흰색 카드
    with st.container():
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        
        col_input, col_list = st.columns([1, 1.2], gap="large")
        
        # [왼쪽] 입력 폼
        with col_input:
            st.subheader("📝 정보 입력")
            with st.form("spec_maker_form", clear_on_submit=True):
                st.caption("기본 정보")
                prod_name = st.text_input("제품명", "MEN'S T-SHIRTS")
                prod_code = st.text_input("품번 (필수)", placeholder="예: BKFTM1581")
                prod_rrp = st.text_input("가격 (RRP)", "Undecided")
                
                st.caption("이미지 & 디자인")
                main_img = st.file_uploader("메인 이미지", type=['png', 'jpg'])
                
                c1, c2 = st.columns(2)
                with c1: 
                    sel_logo = st.selectbox("로고", ["선택 없음"] + get_files(LOGO_DIR))
                with c2: 
                    sel_art = st.selectbox("아트워크", ["선택 없음"] + get_files(ARTWORK_DIR))
                
                st.caption("컬러웨이 (최대 3개)")
                c_data = []
                for i in range(3):
                    cc1, cc2 = st.columns([1, 2])
                    with cc1: ci = st.file_uploader(f"Img{i+1}", type=['png','jpg'], key=f"ci{i}", label_visibility="collapsed")
                    with cc2: cn = st.text_input(f"Nm{i+1}", placeholder="색상명", key=f"cn{i}", label_visibility="collapsed")
                    if ci and cn: c_data.append({"img": ci, "name": cn})
                    st.write("") # 간격

                submit = st.form_submit_button("리스트에 추가")
                
                if submit:
                    if not prod_code or not main_img:
                        st.error("품번과 메인 이미지는 필수입니다.")
                    else:
                        st.session_state.product_list.append({
                            "name": prod_name, "code": prod_code, "rrp": prod_rrp,
                            "main_image": main_img, "logo": sel_logo, "artwork": sel_art,
                            "colors": c_data
                        })
                        st.success("추가되었습니다.")

        # [오른쪽] 리스트 및 다운로드
        with col_list:
            r1, r2 = st.columns([3, 1])
            with r1: st.subheader(f"📋 생성 대기 목록 ({len(st.session_state.product_list)})")
            with r2: 
                if st.button("초기화"):
                    st.session_state.product_list = []
                    st.rerun()
            
            if not st.session_state.product_list:
                st.info("왼쪽 폼에서 데이터를 추가해주세요.")
            else:
                for idx, item in enumerate(st.session_state.product_list):
                    with st.expander(f"{idx+1}. {item['code']}", expanded=False):
                        st.write(f"**{item['name']}**")
                        if item['logo'] != "선택 없음": st.caption(f"Logo: {item['logo']}")
                        st.caption(f"Colors: {len(item['colors'])}개")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚀 PPT 파일 생성하기", type="primary"):
                    ppt_io = create_pptx(st.session_state.product_list)
                    st.download_button("📥 다운로드 (.pptx)", ppt_io, "SpecSheet.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")

        st.markdown('</div>', unsafe_allow_html=True) # 카드 닫기

# 3. 자산 관리 (Assets)
elif "자산" in menu:
    st.title("자산 관리")
    st.markdown("PPT 생성에 사용될 로고와 아트워크 파일을 관리합니다.")
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        
        # 탭 대신 라디오 버튼을 가로로 배치하거나 그냥 2단 컬럼 사용
        col_type, col_upload = st.columns([1, 2])
        
        with col_type:
            asset_type = st.radio("폴더 선택", ["Logos (로고)", "Artworks (아트워크)"])
            target_dir = LOGO_DIR if "Logos" in asset_type else ARTWORK_DIR
            
        with col_upload:
            uploaded = st.file_uploader(f"{asset_type} 파일 업로드", type=['png', 'jpg'], accept_multiple_files=True)
            if uploaded and st.button("서버에 저장"):
                for f in uploaded: save_uploaded_file(f, target_dir)
                st.success("저장 완료!")
                st.rerun()
        
        st.markdown("---")
        
        files = get_files(target_dir)
        st.subheader(f"파일 목록 ({len(files)}개)")
        
        if not files:
            st.warning("파일이 없습니다.")
        else:
            cols = st.columns(5)
            for i, f_name in enumerate(files):
                with cols[i%5]:
                    f_path = os.path.join(target_dir, f_name)
                    st.image(f_path, use_container_width=True)
                    st.caption(f_name)
                    if st.button("삭제", key=f"del_{f_name}"):
                        delete_file(target_dir, f_name)
                        st.rerun()
                        
        st.markdown('</div>', unsafe_allow_html=True)