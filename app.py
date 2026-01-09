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

# --- 기능 로직 (변경 없음) ---
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
# 🎨 UI & CSS (Toss Design System Applied)
# =========================================================
st.set_page_config(page_title="BOSS Spec Maker", layout="wide")
init_folders()

# CSS Injection
st.markdown("""
<style>
    /* 1. 기본 폰트 및 배경 설정 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [class*="css"]  {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
        background-color: #F2F4F6; /* 토스 배경색 */
        color: #191F28; /* 기본 텍스트 블랙 */
    }
    
    /* 2. 메인 컨테이너 스타일 */
    .stApp {
        background-color: #F2F4F6;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* 3. 입력 필드 (Input) 스타일 - 회색 배경, 둥근 모서리(Small R) */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #ffffff;
        border: 1px solid #E5E8EB;
        border-radius: 12px !important; /* R값 축소 (12px) */
        color: #333D4B;
    }
    div[data-baseweb="input"] > div:focus-within {
        border-color: #3182F6 !important; /* 토스 블루 */
        box-shadow: 0 0 0 1px #3182F6 !important;
    }
    
    /* 4. 버튼 (Button) 스타일 */
    div.stButton > button {
        background-color: #3182F6 !important; /* 토스 블루 */
        color: white !important;
        border-radius: 12px !important; /* R값 축소 */
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        font-size: 14px !important; /* 폰트 사이즈 축소 */
        box-shadow: 0 2px 8px rgba(49, 130, 246, 0.15);
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #1B64DA !important;
        transform: translateY(-1px);
    }
    div.stButton > button:active {
        transform: scale(0.98);
    }
    
    /* 보조 버튼 (목록 비우기 등) 스타일 오버라이딩 */
    button[kind="secondary"] {
        background-color: #E8F3FF !important;
        color: #3182F6 !important;
    }

    /* 5. 카드형 레이아웃 (Expander 등) */
    .streamlit-expanderHeader {
        background-color: white;
        border-radius: 12px;
        border: 1px solid #E5E8EB;
        font-weight: 600;
        color: #333D4B;
    }
    div[data-testid="stExpander"] {
        background-color: white;
        border-radius: 12px;
        border: none;
        box-shadow: 0 2px 12px rgba(0,0,0,0.03);
        margin-bottom: 10px;
    }
    
    /* 6. 탭 (Tabs) 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: #8B95A1;
        font-weight: 600;
        font-size: 15px;
    }
    .stTabs [aria-selected="true"] {
        background-color: white !important;
        color: #3182F6 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    /* 7. 제목 및 텍스트 */
    h1 { font-size: 28px !important; font-weight: 700 !important; color: #191F28 !important; margin-bottom: 1rem !important; }
    h2 { font-size: 22px !important; font-weight: 700 !important; color: #333D4B !important; }
    h3 { font-size: 18px !important; font-weight: 600 !important; color: #333D4B !important; }
    p, label { font-size: 14px !important; color: #4E5968 !important; }

    /* 구분선 */
    hr { margin: 1.5em 0; border-color: #E5E8EB; }

</style>
""", unsafe_allow_html=True)

# 헤더 영역
st.title("BOSS Spec Maker")

# 탭 메뉴
tab_main, tab_asset = st.tabs(["PPT Generator", "Asset Manager"])

# =========================================================
# 탭 1: PPT 제작
# =========================================================
with tab_main:
    # 레이아웃: 왼쪽(입력) / 오른쪽(리스트)
    col_input, col_list = st.columns([1, 1.8], gap="large")
    
    # [좌측] 입력 폼
    with col_input:
        st.markdown("### Product Info")
        with st.container(): # 흰색 카드 느낌을 주기 위한 컨테이너
            with st.form("add_product_form", clear_on_submit=True):
                st.caption("기본 정보")
                prod_name = st.text_input("제품명", "MEN'S T-SHIRTS")
                prod_code = st.text_input("품번 (필수)", placeholder="BKFTM1581")
                prod_rrp = st.text_input("가격 (RRP)", "Undecided")
                
                st.caption("디자인 소스")
                main_img = st.file_uploader("메인 이미지", type=['png', 'jpg', 'jpeg'])
                
                logo_list = ["선택 없음"] + get_files(LOGO_DIR)
                art_list = ["선택 없음"] + get_files(ARTWORK_DIR)
                c1, c2 = st.columns(2)
                with c1: sel_logo = st.selectbox("로고", logo_list)
                with c2: sel_artwork = st.selectbox("아트워크", art_list)
                
                st.caption("컬러웨이 (Colorways)")
                c_data = []
                # 공간 절약을 위해 Expander 사용
                with st.expander("컬러 입력 열기 (최대 3개)", expanded=True):
                    for i in range(3):
                        cc1, cc2 = st.columns([1, 2])
                        with cc1: ci = st.file_uploader(f"Img {i+1}", type=['png','jpg'], key=f"ci_{i}", label_visibility="collapsed")
                        with cc2: cn = st.text_input(f"Name {i+1}", placeholder="색상명", key=f"cn_{i}", label_visibility="collapsed")
                        if ci and cn: c_data.append({"img": ci, "name": cn})
                        st.markdown("<div style='margin-bottom:5px'></div>", unsafe_allow_html=True)

                st.markdown("---")
                add_btn = st.form_submit_button("리스트에 추가하기", use_container_width=True)
                
                if add_btn:
                    if not prod_code or not main_img:
                        st.error("품번과 메인 이미지를 입력해주세요.")
                    else:
                        new_item = {
                            "name": prod_name, "code": prod_code, "rrp": prod_rrp,
                            "main_image": main_img, "logo": sel_logo, "artwork": sel_artwork,
                            "colors": c_data
                        }
                        st.session_state.product_list.append(new_item)
                        st.success(f"{prod_code} 추가 완료")

    # [우측] 리스트 및 생성
    with col_list:
        st.markdown(f"### Queue ({len(st.session_state.product_list)})")
        
        # 상단 액션 바
        ac_col1, ac_col2 = st.columns([4, 1])
        with ac_col2:
            if st.button("초기화", key="clear_all"):
                st.session_state.product_list = []
                st.rerun()

        if len(st.session_state.product_list) == 0:
            st.info("왼쪽에서 제품 정보를 입력하고 추가해주세요.")
        else:
            # 리스트 아이템 디자인
            for idx, item in enumerate(st.session_state.product_list):
                # 카드 스타일 커스텀
                with st.expander(f"{idx+1}. {item['code']}  |  {item['name']}", expanded=False):
                    ic1, ic2 = st.columns([1, 4])
                    with ic1:
                        st.image(item['main_image'], width=80)
                    with ic2:
                        st.caption(f"Logo: {item['logo']} / Artwork: {item['artwork']}")
                        colors_str = ", ".join([c['name'] for c in item['colors']])
                        st.write(f"Colors: {colors_str}")

            st.markdown("---")
            if st.button("PPT 생성 및 다운로드", type="primary", use_container_width=True):
                ppt_io = create_pptx(st.session_state.product_list)
                st.download_button("📥 .pptx 파일 저장", ppt_io, "SpecSheet_Result.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)

# =========================================================
# 탭 2: 자산 관리
# =========================================================
with tab_asset:
    st.markdown("### Assets Manager")
    
    asset_type = st.radio("폴더 선택", ["Logos", "Artworks"], horizontal=True, label_visibility="collapsed")
    target_dir = LOGO_DIR if asset_type == "Logos" else ARTWORK_DIR
    
    # 업로드 영역 (카드 스타일)
    with st.expander("📂 파일 업로드 열기", expanded=True):
        uploaded_files = st.file_uploader(f"{asset_type} 폴더에 추가할 파일", type=['png', 'jpg'], accept_multiple_files=True)
        if uploaded_files:
            if st.button("서버에 저장하기", use_container_width=True):
                for uf in uploaded_files:
                    save_uploaded_file(uf, target_dir)
                st.success("저장되었습니다.")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 갤러리 영역
    files = get_files(target_dir)
    st.caption(f"저장된 파일: {len(files)}개")
    
    if not files:
        st.warning("파일이 없습니다.")
    else:
        cols = st.columns(5) # 5열 그리드 (더 작게)
        for i, file_name in enumerate(files):
            col = cols[i % 5]
            with col:
                file_path = os.path.join(target_dir, file_name)
                st.image(file_path, use_container_width=True)
                
                # 작은 관리 버튼
                with st.popover("설정", use_container_width=True):
                    st.caption(file_name)
                    new_name = st.text_input("이름 변경", value=file_name, key=f"ren_{file_name}")
                    if st.button("변경", key=f"b_ren_{file_name}"):
                        s, m = rename_file(target_dir, file_name, new_name)
                        if s: st.rerun()
                        else: st.error(m)
                    
                    if st.button("삭제", key=f"b_del_{file_name}", type="primary"):
                        delete_file(target_dir, file_name)
                        st.rerun()