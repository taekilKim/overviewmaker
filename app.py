import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit_antd_components as sac # [NEW] 전문적인 사이드바 메뉴용
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
    return [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.svg'))]

# --- 깃허브 연동 함수 ---
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

        # Text
        tb = slide.shapes.add_textbox(Mm(15), Mm(15), Mm(130), Mm(30))
        tb.text_frame.text = f"{data['name']}\n{data['code']}"
        tb.text_frame.paragraphs[0].font.size = Pt(24)
        tb.text_frame.paragraphs[0].font.bold = True
        try: tb.text_frame.paragraphs[0].font.name = 'Inter' # 디자인에 맞게 Inter로 변경
        except: pass
        
        rrp = slide.shapes.add_textbox(Mm(250), Mm(15), Mm(50), Mm(15))
        rrp.text_frame.text = f"RRP : {data['rrp']}"
        rrp.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

        if data['main_image']:
            slide.shapes.add_picture(data['main_image'], left=Mm(20), top=Mm(60), width=Mm(140))
        if data['logo'] and data['logo'] != "None":
            p_logo = os.path.join(LOGO_DIR, data['logo'])
            if os.path.exists(p_logo): slide.shapes.add_picture(p_logo, left=Mm(180), top=Mm(60), width=Mm(40))
        if data['artwork'] and data['artwork'] != "None":
            p_art = os.path.join(ARTWORK_DIR, data['artwork'])
            if os.path.exists(p_art): slide.shapes.add_picture(p_art, left=Mm(180), top=Mm(110), width=Mm(40))

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
st.set_page_config(page_title="Admin Kit", layout="wide", initial_sidebar_state="expanded")
init_folders()
load_css(CSS_FILE)

if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# --- 1. 좌측 사이드바 (Admin Style Navigation) ---
with st.sidebar:
    # (1) 로고 영역
    if os.path.exists(SIDEBAR_LOGO):
        st.image(SIDEBAR_LOGO, width=140)
    else:
        st.markdown("### BOSS Golf")
    
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # (2) 전문적인 메뉴 구성 (sac 라이브러리 사용)
    # 아이콘은 Bootstrap Icons (bs) 사용
    selected_menu = sac.menu([
        sac.MenuItem('Dashboard', icon='grid-fill'), # Overview
        sac.MenuItem('Spec Maker', icon='file-earmark-plus-fill'), # PPT Maker
        sac.MenuItem('Assets', icon='images', children=[ # Nested Menu
            sac.MenuItem('Logos', icon='box-seam'),
            sac.MenuItem('Artworks', icon='brush'),
        ]),
        sac.MenuItem(type='divider'),
        sac.MenuItem('Settings', icon='gear', disabled=True),
    ], size='sm', color='dark', open_all=True)

    st.markdown("<div style='margin-top: auto;'></div>", unsafe_allow_html=True)
    
    # 하단 깃허브 상태
    if get_github_repo():
        ui.badges(badge_list=[("GitHub Sync", "secondary")], key="gh_status")
    else:
        ui.badges(badge_list=[("Local Mode", "outline")], key="local_status")


# --- 2. 메인 콘텐츠 영역 (White Cards) ---

# [PAGE] Dashboard
if selected_menu == 'Dashboard':
    # Breadcrumbs & Header
    st.markdown("#### Dashboard > Overview")
    st.title("Overview")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Metric Cards (Shadcn Style)
    cols = st.columns(3)
    with cols[0]:
        ui.metric_card(title="Pending Specs", content=f"{len(st.session_state.product_list)}", description="Ready to generate", key="m1")
    with cols[1]:
        ui.metric_card(title="Total Assets", content=f"{len(get_files(LOGO_DIR)) + len(get_files(ARTWORK_DIR))}", description="Logos & Artworks", key="m2")
    with cols[2]:
        ui.metric_card(title="System Status", content="Active", description="Version 1.2.0", key="m3")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Recent Activity (Shadcn Card)
    st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
    st.markdown("### Recent Activity")
    st.markdown("Your recent specification sheet generation tasks.")
    st.markdown("---")
    if not st.session_state.product_list:
        st.info("No active tasks.")
    else:
        for item in st.session_state.product_list[-3:]: # Show last 3
            st.markdown(f"**{item['code']}** - {item['name']}")
    st.markdown('</div>', unsafe_allow_html=True)


# [PAGE] Spec Maker
elif selected_menu == 'Spec Maker':
    st.markdown("#### Dashboard > Spec Maker")
    st.title("Create Specifications")
    st.markdown("<br>", unsafe_allow_html=True)

    # 탭으로 분리
    tab1, tab2 = st.tabs(["Editor", "Queue"])
    
    with tab1:
        st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
        st.markdown("### Product Details")
        st.caption("Enter the product information below.")
        
        with st.form("spec_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            with c1:
                p_name = st.text_input("Product Name", "MEN'S T-SHIRTS")
                p_code = st.text_input("Product Code", placeholder="BKFTM1581")
            with c2:
                p_rrp = st.text_input("RRP", "Undecided")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### Assets & Colors")
            
            c3, c4, c5 = st.columns([2, 1, 1])
            with c3: main_img = st.file_uploader("Main Image", type=['png','jpg'])
            with c4: s_logo = st.selectbox("Logo", ["None"] + get_files(LOGO_DIR))
            with c5: s_art = st.selectbox("Artwork", ["None"] + get_files(ARTWORK_DIR))
            
            st.markdown("---")
            colors = []
            for i in range(3):
                col_a, col_b = st.columns([1, 2])
                with col_a: ci = st.file_uploader(f"Color {i+1} Img", type=['png','jpg'], key=f"ci{i}")
                with col_b: cn = st.text_input(f"Color {i+1} Name", key=f"cn{i}")
                if ci and cn: colors.append({"img":ci, "name":cn})
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Add to Queue", type="primary"):
                if not p_code or not main_img:
                    st.error("Code and Main Image are required.")
                else:
                    st.session_state.product_list.append({
                        "name":p_name, "code":p_code, "rrp":p_rrp, 
                        "main_image":main_img, "logo":s_logo, "artwork":s_art, "colors":colors
                    })
                    st.success(f"Added {p_code} to queue.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
        c_head, c_btn = st.columns([4, 1])
        with c_head: st.markdown(f"### Generation Queue ({len(st.session_state.product_list)})")
        with c_btn:
            if ui.button("Clear All", variant="outline", key="clear"):
                st.session_state.product_list = []
                st.rerun()
        
        if not st.session_state.product_list:
            st.info("Queue is empty. Go to 'Editor' tab to add items.")
        else:
            # 테이블 형식으로 보여주기 (Shadcn Table 느낌)
            for idx, item in enumerate(st.session_state.product_list):
                with st.expander(f"{idx+1}. {item['code']} - {item['name']}"):
                    cols = st.columns([1, 4])
                    cols[0].image(item['main_image'])
                    cols[1].write(f"Colors: {len(item['colors'])} | Logo: {item['logo']}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Download PPT", type="primary"):
                ppt = create_pptx(st.session_state.product_list)
                st.download_button("Click to Download", ppt, "SpecSheet.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        st.markdown('</div>', unsafe_allow_html=True)


# [PAGE] Assets (Logos & Artworks)
elif selected_menu in ['Logos', 'Artworks']:
    st.markdown(f"#### Assets > {selected_menu}")
    st.title(f"{selected_menu} Library")
    st.markdown("<br>", unsafe_allow_html=True)
    
    target_dir = LOGO_DIR if selected_menu == 'Logos' else ARTWORK_DIR
    
    # 1. Upload Card
    st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
    st.markdown("### Upload New Assets")
    uploaded = st.file_uploader("Drag and drop files here", type=['png','jpg','svg'], accept_multiple_files=True)
    if uploaded and st.button("Upload to Storage"):
        with st.spinner("Processing..."):
            for f in uploaded: upload_file(f, target_dir)
        st.success("Upload complete.")
        time.sleep(1)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 2. Grid View
    st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
    files = get_files(target_dir)
    st.markdown(f"### Library ({len(files)} items)")
    if not files:
        st.info("No files found.")
    else:
        cols = st.columns(5)
        for i, f in enumerate(files):
            with cols[i%5]:
                st.image(os.path.join(target_dir, f), use_container_width=True)
                st.caption(f)
                if st.button("Delete", key=f"del_{f}"):
                    delete_file_asset(f, target_dir)
                    time.sleep(1)
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)