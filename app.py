import streamlit as st
import streamlit_shadcn_ui as ui
from pptx import Presentation
from pptx.util import Mm, Pt
from pptx.enum.text import PP_ALIGN
import io
import os
import time

# GitHub 라이브러리 로드
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

# --- 설정 ---
TEMPLATE_FILE = "template.pptx"
SIDEBAR_LOGO = "assets/bossgolf.svg" # [브랜드] 로고 파일
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

# --- 깃허브 함수 (생략 없이 유지) ---
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
        try: tb.text_frame.paragraphs[0].font.name = 'Pretendard'
        except: pass
        
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
# APP MAIN
# =========================================================
st.set_page_config(page_title="BOSS Golf Admin", layout="wide", initial_sidebar_state="expanded")
init_folders()
load_css(CSS_FILE)

if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# --- 1. 좌측 사이드바 (Navigation) ---
with st.sidebar:
    # 로고
    if os.path.exists(SIDEBAR_LOGO):
        st.image(SIDEBAR_LOGO, width=150)
    else:
        st.markdown("## BOSS Golf")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 뱃지
    ui.badges(badge_list=[("BOSS Golf Admin", "default")], key="admin_badge")
    
    st.markdown("---")
    
    # 메뉴
    menu = st.radio("MENU", ["Spec Maker", "Asset Manager"], label_visibility="collapsed")
    
    st.markdown("---")
    if get_github_repo():
        st.caption("🟢 GitHub Connected")
    else:
        st.caption("⚪ Local Mode")


# --- 2. 우측 콘텐츠 영역 (Card Layout) ---

# [메뉴 1] PPT 스펙 메이커
if menu == "Spec Maker":
    st.title("Spec Sheet Maker")
    
    # 탭 메뉴
    tab_form, tab_list = st.tabs(["📝 Input", "📋 Queue"])
    
    with tab_form:
        # [중요] 토스 스타일 흰색 카드 시작
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        
        st.markdown("### Product Details")
        with st.form("spec_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            with c1:
                prod_name = st.text_input("Product Name", "MEN'S T-SHIRTS")
                prod_code = st.text_input("Product Code", placeholder="e.g. BKFTM1581")
            with c2:
                prod_rrp = st.text_input("RRP", "Undecided")
            
            st.markdown("### Assets")
            c3, c4, c5 = st.columns([2, 1, 1])
            with c3:
                main_img = st.file_uploader("Main Image", type=['png', 'jpg'])
            with c4:
                sel_logo = st.selectbox("Logo", ["선택 없음"] + get_files(LOGO_DIR))
            with c5:
                sel_art = st.selectbox("Artwork", ["선택 없음"] + get_files(ARTWORK_DIR))
            
            st.markdown("### Colorways")
            colors = []
            for i in range(3):
                cc1, cc2 = st.columns([1, 2])
                with cc1: ci = st.file_uploader(f"Image {i+1}", type=['png', 'jpg'], key=f"ci{i}")
                with cc2: cn = st.text_input(f"Name {i+1}", key=f"cn{i}")
                if ci and cn: colors.append({"img": ci, "name": cn})
                st.write("") # 간격
            
            st.markdown("---")
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
        
        st.markdown('</div>', unsafe_allow_html=True) # 카드 닫기

    with tab_list:
        # [중요] 토스 스타일 흰색 카드 시작
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        
        c_head, c_btn = st.columns([4, 1])
        with c_head: st.markdown(f"### Pending Items ({len(st.session_state.product_list)})")
        with c_btn:
            if ui.button("Clear All", variant="outline", key="clear"):
                st.session_state.product_list = []
                st.rerun()
        
        if not st.session_state.product_list:
            st.info("No items in queue.")
        else:
            for idx, item in enumerate(st.session_state.product_list):
                with st.expander(f"{idx+1}. {item['code']} - {item['name']}"):
                    c_img, c_info = st.columns([1, 5])
                    with c_img: st.image(item['main_image'])
                    with c_info: st.write(f"Colors: {len(item['colors'])} | Logo: {item['logo']}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Generate PPT", type="primary"):
                with st.spinner("Generating..."):
                    ppt = create_pptx(st.session_state.product_list)
                st.success("Done!")
                st.download_button("Download .pptx", ppt, "BOSS_Golf_Spec.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        
        st.markdown('</div>', unsafe_allow_html=True) # 카드 닫기

# [메뉴 2] 자산 관리
elif menu == "Asset Manager":
    st.title("Asset Manager")
    
    # 탭 메뉴 (Logos / Artworks)
    active_tab = ui.tabs(options=['Logos', 'Artworks'], defaultValue='Logos', key="asset_tabs")
    target_dir = LOGO_DIR if active_tab == 'Logos' else ARTWORK_DIR
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 1. 업로드 카드
    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
    st.markdown(f"### Upload to {active_tab}")
    
    uploaded = st.file_uploader(f"Choose files", type=['png', 'jpg', 'svg'], accept_multiple_files=True)
    if uploaded and st.button("Save to Storage"):
        with st.spinner("Saving..."):
            cnt = 0
            for f in uploaded:
                if upload_file(f, target_dir): cnt += 1
            if cnt:
                st.success(f"{cnt} files saved.")
                time.sleep(1)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. 갤러리 카드
    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
    files = get_files(target_dir)
    st.markdown(f"### Library ({len(files)})")
    
    if not files:
        st.info("Empty folder.")
    else:
        cols = st.columns(5)
        for i, f in enumerate(files):
            with cols[i%5]:
                # 이미지 컨테이너
                st.image(os.path.join(target_dir, f), use_container_width=True)
                st.caption(f)
                if st.button("Delete", key=f"del_{f}"):
                    delete_file_asset(f, target_dir)
                    time.sleep(1)
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)