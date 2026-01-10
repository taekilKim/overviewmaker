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
        try: tb.text_frame.paragraphs[0].font.name = 'Inter'
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
st.set_page_config(page_title="BOSS Golf Admin", layout="wide", initial_sidebar_state="expanded")
init_folders()
load_css(CSS_FILE)

if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# --- 1. 좌측 사이드바 (Navigation) ---
with st.sidebar:
    if os.path.exists(SIDEBAR_LOGO):
        st.image(SIDEBAR_LOGO, width=140)
    else:
        st.markdown("### BOSS Golf")
    
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # [수정] 대시보드 제거, Spec Maker를 최상단으로 이동
    selected_menu = sac.menu([
        sac.MenuItem('Spec Maker', icon='file-earmark-plus-fill'), # 1. 메인 기능
        sac.MenuItem('Assets', icon='box-seam', children=[         # 2. 자산 관리
            sac.MenuItem('Logos', icon='image'),
            sac.MenuItem('Artworks', icon='brush'),
        ]),
    ], size='sm', color='dark', open_all=True)

    st.markdown("<div style='margin-top: auto;'></div>", unsafe_allow_html=True)
    
    if get_github_repo():
        ui.badges(badge_list=[("GitHub Sync", "secondary")], key="gh_status")
    else:
        ui.badges(badge_list=[("Local Mode", "outline")], key="local_status")


# --- 2. 메인 콘텐츠 영역 ---

# [PAGE] Spec Maker (기본 홈 화면)
if selected_menu == 'Spec Maker':
    st.title("Spec Sheet Maker")
    st.markdown("Create new product specification sheets.")
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Editor", "Queue"])
    
    # 탭 1: 입력 에디터
    with tab1:
        st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
        st.markdown("### Product Info")
        
        with st.form("spec_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            with c1:
                p_name = st.text_input("Product Name", "MEN'S T-SHIRTS")
                p_code = st.text_input("Product Code", placeholder="BKFTM1581")
            with c2:
                p_rrp = st.text_input("RRP", "Undecided")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### Design Assets")
            
            c3, c4, c5 = st.columns([2, 1, 1])
            with c3: main_img = st.file_uploader("Main Image", type=['png','jpg'])
            with c4: s_logo = st.selectbox("Logo", ["None"] + get_files(LOGO_DIR))
            with c5: s_art = st.selectbox("Artwork", ["None"] + get_files(ARTWORK_DIR))
            
            st.markdown("---")
            st.markdown("### Colorways")
            colors = []
            for i in range(3):
                col_a, col_b = st.columns([1, 2])
                with col_a: ci = st.file_uploader(f"Img {i+1}", type=['png','jpg'], key=f"ci{i}", label_visibility="collapsed")
                with col_b: cn = st.text_input(f"Name {i+1}", placeholder=f"Color {i+1}", key=f"cn{i}", label_visibility="collapsed")
                if ci and cn: colors.append({"img":ci, "name":cn})
                st.write("") # Margin
            
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

    # 탭 2: 대기열 목록
    with tab2:
        st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
        c_head, c_btn = st.columns([4, 1])
        with c_head: st.markdown(f"### Queue ({len(st.session_state.product_list)})")
        with c_btn:
            if ui.button("Clear All", variant="outline", key="clear"):
                st.session_state.product_list = []
                st.rerun()
        
        if not st.session_state.product_list:
            st.info("No items in queue. Use 'Editor' tab to add products.")
        else:
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


# [PAGE] Assets
elif selected_menu in ['Logos', 'Artworks']:
    st.title(f"{selected_menu} Library")
    st.markdown(f"Manage your {selected_menu.lower()} here.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    target_dir = LOGO_DIR if selected_menu == 'Logos' else ARTWORK_DIR
    
    # 1. Upload
    st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
    st.markdown("### Upload")
    uploaded = st.file_uploader("Drag and drop files", type=['png','jpg','svg'], accept_multiple_files=True)
    if uploaded and st.button("Upload to Storage"):
        with st.spinner("Processing..."):
            for f in uploaded: upload_file(f, target_dir)
        st.success("Upload complete.")
        time.sleep(1)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 2. Gallery
    st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
    files = get_files(target_dir)
    st.markdown(f"### Library ({len(files)})")
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