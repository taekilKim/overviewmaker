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

# --- 기능 로직 (이전과 동일) ---
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
# 🎨 UI & CSS (REAL TDS Style)
# =========================================================
st.set_page_config(page_title="BOSS Spec Maker", layout="wide")
init_folders()

# CSS Injection: Pretendard 폰트 + 깔끔한 토스 스타일
st.markdown("""
<style>
    /* 1. 폰트 임베딩 (Pretendard) */
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

    html, body, .stApp {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
        background-color: #F9FAFB !important; /* 아주 연한 회색 (Clean) */
        color: #191F28 !important; /* 토스 블랙 */
    }

    /* 2. 제목 스타일 */
    h1 {
        font-size: 26px !important;
        font-weight: 700 !important;
        color: #191F28 !important;
        letter-spacing: -0.5px;
    }
    h2, h3 {
        font-weight: 600 !important;
        color: #333D4B !important; /* 다크 그레이 */
        letter-spacing: -0.3px;
    }

    /* 3. 입력 필드 (Inputs) - 흰색 배경에 깔끔한 보더 */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stFileUploader {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E8EB !important; /* 연한 회색 라인 */
        border-radius: 8px !important; /* R값 8px로 축소 */
        color: #333D4B !important;
        font-size: 15px !important;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: #3182F6 !important; /* 포커스 시 토스 블루 */
        box-shadow: 0 0 0 1px #3182F6 !important;
    }

    /* 4. 메인 버튼 (Primary) - 선명한 블루 */
    div.stButton > button {
        width: 100%;
        background-color: #3182F6 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important; /* 버튼 R값 8px */
        padding: 0.6rem 1rem !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 6px rgba(49, 130, 246, 0.15);
        transition: opacity 0.2s;
    }
    div.stButton > button:hover {
        opacity: 0.9;
        box-shadow: 0 4px 12px rgba(49, 130, 246, 0.25);
    }
    div.stButton > button:active {
        background-color: #1B64DA !important;
    }

    /* 5. 보조 버튼 (Secondary) - 삭제, 초기화 등 */
    /* Streamlit은 버튼 클래스 구분이 어려워, 특정 키워드가 들어간 버튼을 타겟팅하긴 어렵습니다. 
       대신 '목록 초기화' 같은 버튼은 UI 배치로 구분했습니다. */

    /* 6. Expander (카드 형태) */
    .streamlit-expanderHeader {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #F2F4F6 !important;
        color: #333D4B !important;
        font-weight: 600 !important;
    }
    div[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #E5E8EB !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }

    /* 7. 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        border-bottom: 1px solid #E5E8EB;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding-bottom: 12px;
        background-color: transparent;
        border: none;
        color: #8B95A1; /* 비활성: 회색 */
        font-weight: 600;
        font-size: 16px;
    }
    .stTabs [aria-selected="true"] {
        color: #191F28 !important; /* 활성: 검정 */
        border-bottom: 2px solid #191F28 !important; /* 밑줄 */
    }
    
    /* 8. 기타 텍스트 */
    p, label {
        color: #4E5968 !important; /* 미디엄 그레이 */
        font-size: 14px !important;
    }
    .small-font {
        font-size: 13px;
        color: #8B95A1;
    }

</style>
""", unsafe_allow_html=True)

# 헤더 영역
st.title("BOSS Spec Maker")
st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# 탭 메뉴
tab_main, tab_asset = st.tabs(["PPT Generator", "Asset Manager"])

# =========================================================
# 탭 1: PPT 제작
# =========================================================
with tab_main:
    col_input, col_list = st.columns([1, 1.5], gap="large")
    
    # [좌측] 입력 폼
    with col_input:
        st.subheader("제품 정보 입력")
        
        with st.form("add_product_form", clear_on_submit=True):
            st.caption("기본 정보")
            prod_name = st.text_input("제품명", "MEN'S T-SHIRTS")
            prod_code = st.text_input("품번 (필수)", placeholder="예: BKFTM1581")
            prod_rrp = st.text_input("가격 (RRP)", "Undecided")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("디자인 리소스")
            main_img = st.file_uploader("메인 이미지", type=['png', 'jpg', 'jpeg'])
            
            logo_list = ["선택 없음"] + get_files(LOGO_DIR)
            art_list = ["선택 없음"] + get_files(ARTWORK_DIR)
            
            c1, c2 = st.columns(2)
            with c1: sel_logo = st.selectbox("로고", logo_list)
            with c2: sel_artwork = st.selectbox("아트워크", art_list)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("컬러웨이 (최대 3개)")
            
            # 컬러 입력부 디자인 간소화
            c_data = []
            with st.container():
                for i in range(3):
                    cc1, cc2 = st.columns([1, 2])
                    with cc1:
                        ci = st.file_uploader(f"img_{i}", type=['png','jpg'], key=f"ci_{i}", label_visibility="collapsed")
                    with cc2:
                        cn = st.text_input(f"name_{i}", placeholder=f"Color {i+1} 이름", key=f"cn_{i}", label_visibility="collapsed")
                    if ci and cn: c_data.append({"img": ci, "name": cn})
                    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

            st.markdown("---")
            add_btn = st.form_submit_button("리스트에 추가")
            
            if add_btn:
                if not prod_code or not main_img:
                    st.error("품번과 메인 이미지는 필수입니다.")
                else:
                    new_item = {
                        "name": prod_name, "code": prod_code, "rrp": prod_rrp,
                        "main_image": main_img, "logo": sel_logo, "artwork": sel_artwork,
                        "colors": c_data
                    }
                    st.session_state.product_list.append(new_item)
                    st.success(f"'{prod_code}' 추가 완료")

    # [우측] 리스트 및 생성
    with col_list:
        c_head, c_btn = st.columns([3, 1])
        with c_head:
            st.subheader(f"생성 대기 목록 ({len(st.session_state.product_list)})")
        with c_btn:
            if st.button("목록 초기화"):
                st.session_state.product_list = []
                st.rerun()

        if len(st.session_state.product_list) == 0:
            st.info("좌측에서 정보를 입력하고 '리스트에 추가' 버튼을 눌러주세요.")
        else:
            # 리스트 아이템 디자인
            for idx, item in enumerate(st.session_state.product_list):
                with st.expander(f"{idx+1}. {item['code']}  |  {item['name']}", expanded=False):
                    ic1, ic2 = st.columns([1, 5])
                    with ic1:
                        st.image(item['main_image'], width=60)
                    with ic2:
                        st.markdown(f"<span class='small-font'>Logo: {item['logo']} | Art: {item['artwork']}</span>", unsafe_allow_html=True)
                        colors_str = ", ".join([c['name'] for c in item['colors']]) if item['colors'] else "없음"
                        st.markdown(f"<span class='small-font'>Colors: {colors_str}</span>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("PPT 생성 및 다운로드", type="primary"):
                ppt_io = create_pptx(st.session_state.product_list)
                st.download_button("📥 .pptx 파일 저장", ppt_io, "SpecSheet_Result.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)

# =========================================================
# 탭 2: 자산 관리
# =========================================================
with tab_asset:
    st.subheader("자산 관리 (Asset Manager)")
    
    asset_type = st.radio("폴더 선택", ["Logos", "Artworks"], horizontal=True, label_visibility="collapsed")
    target_dir = LOGO_DIR if asset_type == "Logos" else ARTWORK_DIR
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 업로드 영역
    with st.expander(f"➕ {asset_type} 파일 업로드", expanded=True):
        uploaded_files = st.file_uploader(f"파일을 드래그하여 추가하세요", type=['png', 'jpg'], accept_multiple_files=True)
        if uploaded_files:
            if st.button("서버에 저장하기", use_container_width=True):
                for uf in uploaded_files:
                    save_uploaded_file(uf, target_dir)
                st.success("저장되었습니다.")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 갤러리 영역
    files = get_files(target_dir)
    st.caption(f"총 {len(files)}개의 파일이 있습니다.")
    
    if not files:
        st.warning("저장된 파일이 없습니다.")
    else:
        # 그리드 레이아웃
        cols = st.columns(5)
        for i, file_name in enumerate(files):
            col = cols[i % 5]
            with col:
                file_path = os.path.join(target_dir, file_name)
                # 이미지 카드
                st.image(file_path, use_container_width=True)
                
                # 팝오버 메뉴
                with st.popover("관리", use_container_width=True):
                    st.caption(file_name)
                    new_name = st.text_input("이름 변경", value=file_name, key=f"ren_{file_name}")
                    if st.button("수정", key=f"b_ren_{file_name}"):
                        s, m = rename_file(target_dir, file_name, new_name)
                        if s: st.rerun()
                        else: st.error(m)
                    
                    st.markdown("---")
                    if st.button("삭제", key=f"b_del_{file_name}"):
                        delete_file(target_dir, file_name)
                        st.rerun()