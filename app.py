import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit_antd_components as sac
from pptx import Presentation
from pptx.util import Mm, Pt
from pptx.enum.text import PP_ALIGN
import io
import os
import time

# GitHub 라이브러리
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

# --- 설정 ---
TEMPLATE_FILE = "template.pptx"
SIDEBAR_LOGO = "assets/bossgolf.svg"
LOGO_DIR = "assets/logos"
ARTWORK_DIR = "assets/artworks"

# --- 유틸리티 함수 ---
def init_folders():
    for folder in [LOGO_DIR, ARTWORK_DIR]:
        if not os.path.exists(folder): os.makedirs(folder)

def get_files(folder_path):
    if not os.path.exists(folder_path): return []
    return [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.svg'))]

# --- 깃허브 연동 ---
def get_github_repo():
    if not GITHUB_AVAILABLE: return None
    try:
        return Github(st.secrets["github"]["token"]).get_repo(st.secrets["github"]["repo_name"])
    except: return None

def upload_file(file_obj, folder_path):
    with open(os.path.join(folder_path, file_obj.name), "wb") as f:
        f.write(file_obj.getbuffer())
    repo = get_github_repo()
    if repo:
        try:
            path = f"{folder_path}/{file_obj.name}"
            content = file_obj.getvalue()
            branch = st.secrets["github"].get("branch", "main")
            try:
                contents = repo.get_contents(path, ref=branch)
                repo.update_file(path, f"Update {file_obj.name}", content, contents.sha, branch=branch)
            except:
                repo.create_file(path, f"Upload {file_obj.name}", content, branch=branch)
            return True
        except: return False
    return True

def delete_file_asset(filename, folder_path):
    local = os.path.join(folder_path, filename)
    if os.path.exists(local): os.remove(local)
    repo = get_github_repo()
    if repo:
        try:
            path = f"{folder_path}/{filename}"
            branch = st.secrets["github"].get("branch", "main")
            contents = repo.get_contents(path, ref=branch)
            repo.delete_file(path, f"Delete {filename}", contents.sha, branch=branch)
        except: pass

# --- PPT 생성 로직 ---
def create_pptx(products):
    if os.path.exists(TEMPLATE_FILE): prs = Presentation(TEMPLATE_FILE)
    else: prs = Presentation()

    for data in products:
        try: slide = prs.slides.add_slide(prs.slide_layouts[1])
        except: slide = prs.slides.add_slide(prs.slide_layouts[0])

        # 텍스트
        tb = slide.shapes.add_textbox(Mm(15), Mm(15), Mm(130), Mm(30))
        tb.text_frame.text = f"{data['name']}\n{data['code']}"
        tb.text_frame.paragraphs[0].font.size = Pt(24)
        tb.text_frame.paragraphs[0].font.bold = True
        
        # RRP (표시만 함)
        if data.get('rrp'):
            rrp = slide.shapes.add_textbox(Mm(250), Mm(15), Mm(50), Mm(15))
            rrp.text_frame.text = f"RRP : {data['rrp']}"
            rrp.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

        # 메인 이미지
        if data['main_image']:
            slide.shapes.add_picture(data['main_image'], left=Mm(20), top=Mm(60), width=Mm(140))
        
        # 로고
        if data['logo'] and data['logo'] != "선택 없음":
            p_logo = os.path.join(LOGO_DIR, data['logo'])
            if os.path.exists(p_logo): slide.shapes.add_picture(p_logo, left=Mm(180), top=Mm(60), width=Mm(40))
        
        # 아트워크 (첫 번째 선택된 것 배치)
        if data['artworks']:
            first_art = data['artworks'][0]
            p_art = os.path.join(ARTWORK_DIR, first_art)
            if os.path.exists(p_art): slide.shapes.add_picture(p_art, left=Mm(180), top=Mm(110), width=Mm(40))

        # 컬러웨이
        sx, sy, w, g = 180, 155, 30, 5
        for i, c in enumerate(data['colors']):
            cx = sx + (i * (w + g))
            if c['img']: slide.shapes.add_picture(c['img'], left=Mm(cx), top=Mm(sy), width=Mm(w))
            tb = slide.shapes.add_textbox(Mm(cx), Mm(sy+32), Mm(w), Mm(10))
            tb.text_frame.text = c['name']
            tb.text_frame.paragraphs[0].font.size = Pt(9)
            tb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output

# =========================================================
# APP MAIN
# =========================================================
st.set_page_config(page_title="BOSS Golf Admin", layout="wide", initial_sidebar_state="expanded")
init_folders()

if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# --- 1. 좌측 사이드바 ---
with st.sidebar:
    if os.path.exists(SIDEBAR_LOGO):
        st.image(SIDEBAR_LOGO, width=140)
    else:
        st.header("BOSS Golf")
    
    st.markdown("---")

    selected_menu = sac.menu([
        sac.MenuItem('슬라이드 제작', icon='file-earmark-plus'),
        sac.MenuItem('로고&아트워크 관리', icon='image'),
    ], size='sm', color='dark', open_all=True)

    st.markdown("---")
    
    # 하단 상태 (간단하게 텍스트로)
    if GITHUB_AVAILABLE:
        st.caption("🟢 GitHub 연동됨")
    else:
        st.caption("⚪ 로컬 모드")


# --- 2. 메인 콘텐츠 ---

if selected_menu == '슬라이드 제작':
    st.title("슬라이드 제작")
    st.markdown("제품 정보를 입력하여 스펙 시트를 생성합니다.")
    st.markdown("---")

    tab_editor, tab_queue = st.tabs(["정보 입력", "생성 대기열"])
    
    # 탭 1: 입력
    with tab_editor:
        # 폼 시작 (카드 CSS 제거됨 - 기본 UI 사용)
        with st.form("spec_form", clear_on_submit=False):
            st.subheader("1. 기본 정보")
            c1, c2 = st.columns([3, 1])
            with c1:
                p_name = st.text_input("제품명", "MEN'S T-SHIRTS")
                p_code = st.text_input("품번 (필수)", placeholder="예: BKFTM1581")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("2. 디자인 자산")
            
            # 메인 이미지
            main_img = st.file_uploader("메인 이미지", type=['png','jpg'], help="슬라이드 좌측에 크게 들어갈 이미지")
            
            c3, c4 = st.columns(2)
            with c3:
                s_logo = st.selectbox("로고 선택", ["선택 없음"] + get_files(LOGO_DIR))
            
            with c4:
                # 아트워크 다중 선택 (Popover)
                available_artworks = get_files(ARTWORK_DIR)
                selected_artworks = []
                
                with st.popover("아트워크 선택하기", use_container_width=True):
                    if not available_artworks:
                        st.warning("등록된 아트워크가 없습니다.")
                    else:
                        for art in available_artworks:
                            ac1, ac2 = st.columns([1, 4])
                            with ac1:
                                is_checked = st.checkbox("V", key=f"chk_{art}", label_visibility="hidden")
                            with ac2:
                                st.image(os.path.join(ARTWORK_DIR, art), width=40)
                                st.caption(art)
                            if is_checked:
                                selected_artworks.append(art)
                
                if selected_artworks:
                    st.caption(f"선택됨: {', '.join(selected_artworks)}")
                else:
                    st.caption("선택된 아트워크 없음")

            st.markdown("---")
            st.subheader("3. 컬러웨이 (Colorways)")
            
            # 일괄 업로드
            uploaded_colors = st.file_uploader("컬러웨이 이미지 일괄 업로드 (최대 4개)", type=['png','jpg'], accept_multiple_files=True)
            colors_input = []
            
            if uploaded_colors:
                st.info(f"{len(uploaded_colors)}개의 이미지가 선택되었습니다. 색상명을 입력해주세요.")
                for idx, c_file in enumerate(uploaded_colors[:4]):
                    col_card, col_input = st.columns([1, 4])
                    with col_card:
                        st.image(c_file, width=60)
                    with col_input:
                        c_name = st.text_input(f"색상명 {idx+1}", key=f"c_name_{idx}")
                    colors_input.append({"img": c_file, "name": c_name})
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 제출
            if st.form_submit_button("대기열에 추가", type="primary"):
                if not p_code or not main_img:
                    st.error("품번과 메인 이미지는 필수입니다.")
                else:
                    st.session_state.product_list.append({
                        "name":p_name, "code":p_code, "rrp":"", 
                        "main_image":main_img, 
                        "logo":s_logo, 
                        "artworks": selected_artworks,
                        "artwork": selected_artworks[0] if selected_artworks else "선택 없음",
                        "colors": colors_input
                    })
                    st.success(f"'{p_code}' 추가 완료!")

    # 탭 2: 대기열
    with tab_queue:
        c_head, c_btn = st.columns([4, 1])
        with c_head: st.subheader(f"생성 대기 목록 ({len(st.session_state.product_list)})")
        with c_btn:
            if st.button("목록 비우기"):
                st.session_state.product_list = []
                st.rerun()
        
        if not st.session_state.product_list:
            st.info("대기 중인 항목이 없습니다.")
        else:
            for idx, item in enumerate(st.session_state.product_list):
                with st.expander(f"{idx+1}. {item['code']} - {item['name']}"):
                    cols = st.columns([1, 4])
                    cols[0].image(item['main_image'])
                    art_str = ", ".join(item['artworks']) if item.get('artworks') else "-"
                    cols[1].write(f"컬러: {len(item['colors'])}개 | 로고: {item['logo']} | 아트워크: {art_str}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("PPT 생성 및 다운로드", type="primary"):
                ppt = create_pptx(st.session_state.product_list)
                st.download_button("PPT 다운로드 (.pptx)", ppt, "BOSS_Golf_SpecSheet.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")


elif selected_menu == '로고&아트워크 관리':
    st.title("자산 관리")
    st.markdown("디자인 자산을 업로드하고 관리합니다.")
    st.markdown("---")
    
    active_tab = ui.tabs(options=['로고', '아트워크'], defaultValue='로고', key="asset_tabs")
    target_dir = LOGO_DIR if active_tab == '로고' else ARTWORK_DIR
    
    st.subheader(f"{active_tab} 업로드")
    uploaded = st.file_uploader("파일 업로드", type=['png','jpg','svg'], accept_multiple_files=True)
    if uploaded and st.button("저장하기"):
        with st.spinner("저장 중..."):
            for f in uploaded: upload_file(f, target_dir)
        st.success("완료")
        time.sleep(1)
        st.rerun()
    
    st.markdown("---")
    st.subheader("보유 파일 목록")
    files = get_files(target_dir)
    
    if not files:
        st.info("파일이 없습니다.")
    else:
        cols = st.columns(5)
        for i, f in enumerate(files):
            with cols[i%5]:
                st.image(os.path.join(target_dir, f), use_container_width=True)
                st.caption(f)
                if st.button("삭제", key=f"del_{f}"):
                    delete_file_asset(f, target_dir)
                    time.sleep(1)
                    st.rerun()