import streamlit as st
import streamlit_shadcn_ui as ui # Shadcn UI 라이브러리
from pptx import Presentation
from pptx.util import Mm, Pt
from pptx.enum.text import PP_ALIGN
import io
import os
import time

# 깃허브 라이브러리 로드
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

# --- 설정 ---
TEMPLATE_FILE = "template.pptx"
LOGO_DIR = "assets/logos"
ARTWORK_DIR = "assets/artworks"
CSS_FILE = "style.css"

# --- 유틸리티 함수 ---
def init_folders():
    for folder in [LOGO_DIR, ARTWORK_DIR]:
        if not os.path.exists(folder): os.makedirs(folder)

def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_files(folder_path):
    if not os.path.exists(folder_path): return []
    return [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

# --- 깃허브 연동 함수 (이전과 동일) ---
def get_github_repo():
    if not GITHUB_AVAILABLE: return None
    try:
        return Github(st.secrets["github"]["token"]).get_repo(st.secrets["github"]["repo_name"])
    except: return None

def upload_file(file_obj, folder_path):
    # 1. 로컬 저장
    with open(os.path.join(folder_path, file_obj.name), "wb") as f:
        f.write(file_obj.getbuffer())
    # 2. 깃허브 저장
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

# --- PPT 생성 로직 (MM 단위) ---
def create_pptx(products):
    if os.path.exists(TEMPLATE_FILE): prs = Presentation(TEMPLATE_FILE)
    else: prs = Presentation()

    for data in products:
        try: slide = prs.slides.add_slide(prs.slide_layouts[1])
        except: slide = prs.slides.add_slide(prs.slide_layouts[0])

        # Text
        tb = slide.shapes.add_textbox(Mm(15), Mm(15), Mm(130), Mm(30))
        tb.text_frame.text = f"{data['name']}\n{data['code']}"
        tb.text_frame.paragraphs[0].font.size = Pt(24)
        tb.text_frame.paragraphs[0].font.bold = True
        
        rrp = slide.shapes.add_textbox(Mm(250), Mm(15), Mm(50), Mm(15))
        rrp.text_frame.text = f"RRP : {data['rrp']}"
        rrp.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

        # Images
        if data['main_image']:
            slide.shapes.add_picture(data['main_image'], left=Mm(20), top=Mm(60), width=Mm(140))
        
        if data['logo'] and data['logo'] != "선택 없음":
            p_logo = os.path.join(LOGO_DIR, data['logo'])
            if os.path.exists(p_logo):
                slide.shapes.add_picture(p_logo, left=Mm(180), top=Mm(60), width=Mm(40))
        
        if data['artwork'] and data['artwork'] != "선택 없음":
            p_art = os.path.join(ARTWORK_DIR, data['artwork'])
            if os.path.exists(p_art):
                slide.shapes.add_picture(p_art, left=Mm(180), top=Mm(110), width=Mm(40))

        # Colors
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
# APP MAIN (Shadcn UI Version)
# =========================================================
st.set_page_config(page_title="BOSS Admin", layout="wide", initial_sidebar_state="expanded")
init_folders()
load_css(CSS_FILE)

if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# --- 사이드바 ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Hugo_Boss_logo.svg/2560px-Hugo_Boss_logo.svg.png", width=120)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Shadcn 스타일의 Badges
    ui.badges(content="Admin Workspace", variant="secondary")
    
    st.markdown("---")
    
    # 네비게이션을 위한 Radio (기존 방식 유지하되 깔끔하게)
    menu = st.radio("MENU", ["Dashboard", "Spec Maker", "Assets"], label_visibility="collapsed")
    
    st.markdown("---")
    if get_github_repo():
        st.caption("🟢 GitHub Connected")
    else:
        st.caption("⚪ Local Mode")

# --- 메인 콘텐츠 ---

# 1. 대시보드
if menu == "Dashboard":
    st.title("Dashboard")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Shadcn Metric Cards (가장 큰 시각적 변화)
    cols = st.columns(3)
    with cols[0]:
        ui.metric_card(title="Pending Specs", content=f"{len(st.session_state.product_list)}", description="Items in Queue", key="card1")
    with cols[1]:
        ui.metric_card(title="Logos", content=f"{len(get_files(LOGO_DIR))}", description="Available Assets", key="card2")
    with cols[2]:
        ui.metric_card(title="Artworks", content=f"{len(get_files(ARTWORK_DIR))}", description="Available Assets", key="card3")

    st.markdown("---")
    st.info("좌측 메뉴에서 작업을 선택하세요.")

# 2. 스펙 시트 제작
elif menu == "Spec Maker":
    st.title("Spec Sheet Maker")
    
    # Shadcn Tabs (입력과 목록을 탭으로 분리)
    # 탭으로 분리하면 공간 활용이 훨씬 좋습니다.
    tab_form, tab_list = st.tabs(["📝 Input Form", "📋 Queue & Export"])
    
    with tab_form:
        # 입력 폼을 카드 안에 넣어서 정리
        with st.container():
            st.markdown("#### Product Details")
            with st.form("spec_form", clear_on_submit=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    prod_name = st.text_input("Product Name", "MEN'S T-SHIRTS")
                    prod_code = st.text_input("Product Code", placeholder="e.g. BKFTM1581")
                with c2:
                    prod_rrp = st.text_input("RRP", "Undecided")
                
                st.markdown("#### Assets")
                c3, c4, c5 = st.columns([2, 1, 1])
                with c3:
                    main_img = st.file_uploader("Main Image", type=['png', 'jpg'])
                with c4:
                    # 파일 목록 로드
                    sel_logo = st.selectbox("Logo", ["선택 없음"] + get_files(LOGO_DIR))
                with c5:
                    sel_art = st.selectbox("Artwork", ["선택 없음"] + get_files(ARTWORK_DIR))
                
                st.markdown("#### Colorways")
                colors = []
                for i in range(3):
                    cc1, cc2 = st.columns([1, 2])
                    with cc1: ci = st.file_uploader(f"Image {i+1}", type=['png', 'jpg'], key=f"ci{i}")
                    with cc2: cn = st.text_input(f"Name {i+1}", key=f"cn{i}")
                    if ci and cn: colors.append({"img": ci, "name": cn})
                    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)
                
                # 폼 제출 버튼
                if st.form_submit_button("Add to Queue", type="primary"):
                    if not prod_code or not main_img:
                        st.error("Code & Main Image are required.")
                    else:
                        st.session_state.product_list.append({
                            "name": prod_name, "code": prod_code, "rrp": prod_rrp,
                            "main_image": main_img, "logo": sel_logo, "artwork": sel_art,
                            "colors": colors
                        })
                        st.success(f"Added: {prod_code}")

    with tab_list:
        st.markdown(f"#### Generated Queue ({len(st.session_state.product_list)})")
        
        col_act1, col_act2 = st.columns([1, 4])
        with col_act1:
            if ui.button("Clear List", variant="outline", key="clear_btn"):
                st.session_state.product_list = []
                st.rerun()
        
        st.markdown("---")
        
        if not st.session_state.product_list:
            st.info("No items in queue.")
        else:
            # 리스트 보여주기
            for idx, item in enumerate(st.session_state.product_list):
                # ui.card는 컨테이너 기능이 약하므로 expander 사용
                with st.expander(f"{idx+1}. {item['code']} - {item['name']}"):
                    c_img, c_info = st.columns([1, 5])
                    with c_img: st.image(item['main_image'])
                    with c_info: st.write(f"Colors: {len(item['colors'])} | Logo: {item['logo']}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            # 다운로드 버튼
            if st.button("🚀 Generate PPT", type="primary"):
                with st.spinner("Processing..."):
                    ppt = create_pptx(st.session_state.product_list)
                st.success("Done!")
                st.download_button("Download .pptx", ppt, "Result.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")

# 3. 자산 관리
elif menu == "Assets":
    st.title("Asset Manager")
    
    # Shadcn Tabs 사용
    active_tab = ui.tabs(options=['Logos', 'Artworks'], defaultValue='Logos', key="asset_tabs")
    
    target_dir = LOGO_DIR if active_tab == 'Logos' else ARTWORK_DIR
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 업로드 섹션
    with st.expander("📤 Upload New Files", expanded=True):
        uploaded = st.file_uploader(f"Upload to {active_tab}", type=['png', 'jpg'], accept_multiple_files=True)
        if uploaded and st.button("Save to GitHub"):
            with st.spinner("Uploading..."):
                cnt = 0
                for f in uploaded:
                    if upload_file(f, target_dir): cnt += 1
                if cnt:
                    st.success(f"{cnt} files saved.")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")
    
    # 갤러리 섹션
    files = get_files(target_dir)
    if not files:
        st.info("No files found.")
    else:
        cols = st.columns(5)
        for i, f in enumerate(files):
            with cols[i%5]:
                st.image(os.path.join(target_dir, f), use_container_width=True)
                # Shadcn 스타일의 작은 버튼은 없어서 native 버튼 사용하되 작게
                if st.button("Delete", key=f"del_{f}"):
                    delete_file_asset(f, target_dir)
                    time.sleep(1)
                    st.rerun()
                st.caption(f)