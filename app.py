import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit_antd_components as sac
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

# --- [상수 설정] ---
TEMPLATE_FILE = "template.pptx"
SIDEBAR_LOGO = "assets/bossgolf.svg"
LOGO_DIR = "assets/logos"
ARTWORK_DIR = "assets/artworks"
CSS_FILE = "style.css"

# --- [유틸리티 함수] ---
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

# --- [GitHub 연동 로직] ---
def get_github_repo():
    if not GITHUB_AVAILABLE: return None
    try:
        return Github(st.secrets["github"]["token"]).get_repo(st.secrets["github"]["repo_name"])
    except: return None

def upload_file(file_obj, folder_path):
    # 로컬 저장
    with open(os.path.join(folder_path, file_obj.name), "wb") as f:
        f.write(file_obj.getbuffer())
    
    # 깃허브 저장
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

# --- [PPT 생성 로직] (MM 단위) ---
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
        try: tb.text_frame.paragraphs[0].font.name = 'Inter'
        except: pass
        
        rrp = slide.shapes.add_textbox(Mm(250), Mm(15), Mm(50), Mm(15))
        rrp.text_frame.text = f"RRP : {data['rrp']}"
        rrp.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

        # 이미지 배치
        if data['main_image']:
            slide.shapes.add_picture(data['main_image'], left=Mm(20), top=Mm(60), width=Mm(140))
        if data['logo'] and data['logo'] != "선택 없음":
            p_logo = os.path.join(LOGO_DIR, data['logo'])
            if os.path.exists(p_logo): slide.shapes.add_picture(p_logo, left=Mm(180), top=Mm(60), width=Mm(40))
        if data['artwork'] and data['artwork'] != "선택 없음":
            p_art = os.path.join(ARTWORK_DIR, data['artwork'])
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
# [앱 메인 실행]
# =========================================================
st.set_page_config(page_title="BOSS Golf Admin", layout="wide", initial_sidebar_state="expanded")
init_folders()
load_css(CSS_FILE)

if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# ---------------------------------------------------------
# 1. 좌측 사이드바 (네비게이션)
# ---------------------------------------------------------
with st.sidebar:
    # 1.1 브랜딩 로고
    if os.path.exists(SIDEBAR_LOGO):
        st.image(SIDEBAR_LOGO, width=150)
    else:
        st.markdown("### BOSS Golf")
    
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

    # 1.2 메뉴 (한글화 완료)
    selected_menu = sac.menu([
        sac.MenuItem('슬라이드 제작', icon='file-earmark-plus-fill'),
        sac.MenuItem('로고/아트워크 관리', icon='images'),
    ], size='sm', color='dark', open_all=True)

    st.markdown("<div style='margin-top: auto;'></div>", unsafe_allow_html=True)
    
    # 1.3 하단 상태 표시 (한글화 완료)
    if get_github_repo():
        ui.badges(badge_list=[("깃허브 연동됨", "secondary")], key="gh_status")
    else:
        ui.badges(badge_list=[("로컬 모드", "outline")], key="local_status")


# ---------------------------------------------------------
# 2. 우측 콘텐츠 영역
# ---------------------------------------------------------

# 2.1 [페이지] 슬라이드 제작 (홈 화면)
if selected_menu == '슬라이드 제작':
    st.title("슬라이드 제작 (Slide Maker)")
    st.markdown("제품 정보를 입력하여 스펙 시트를 생성합니다.")
    st.markdown("<br>", unsafe_allow_html=True)

    # 탭 메뉴
    tab_editor, tab_queue = st.tabs(["정보 입력", "생성 대기열"])
    
    # [탭 1] 정보 입력
    with tab_editor:
        st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
        st.markdown("### 제품 정보 (Product Info)")
        
        with st.form("spec_form", clear_on_submit=True):
            # 기본 정보 입력
            c1, c2 = st.columns([2, 1])
            with c1:
                p_name = st.text_input("제품명", value="MEN'S T-SHIRTS")
                p_code = st.text_input("품번 (필수)", placeholder="예: BKFTM1581")
            with c2:
                p_rrp = st.text_input("가격 (RRP)", value="미정")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 디자인 자산 (Design Assets)")
            
            # 파일 및 프리셋 선택
            c3, c4, c5 = st.columns([2, 1, 1])
            with c3: main_img = st.file_uploader("메인 이미지 업로드", type=['png','jpg'])
            with c4: s_logo = st.selectbox("로고 선택", ["선택 없음"] + get_files(LOGO_DIR))
            with c5: s_art = st.selectbox("아트워크 선택", ["선택 없음"] + get_files(ARTWORK_DIR))
            
            st.markdown("---")
            st.markdown("### 컬러웨이 (Colorways)")
            
            # 컬러 입력 (3개)
            colors = []
            for i in range(3):
                col_a, col_b = st.columns([1, 2])
                with col_a: 
                    ci = st.file_uploader(f"컬러 {i+1} 이미지", type=['png','jpg'], key=f"ci{i}", label_visibility="collapsed")
                with col_b: 
                    cn = st.text_input(f"컬러 {i+1} 색상명", placeholder=f"색상명 {i+1} 입력", key=f"cn{i}", label_visibility="collapsed")
                
                if ci and cn: colors.append({"img":ci, "name":cn})
                st.write("") 
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 제출 버튼
            if st.form_submit_button("대기열에 추가", type="primary"):
                if not p_code or not main_img:
                    st.error("품번과 메인 이미지는 필수 입력 항목입니다.")
                else:
                    st.session_state.product_list.append({
                        "name":p_name, "code":p_code, "rrp":p_rrp, 
                        "main_image":main_img, "logo":s_logo, "artwork":s_art, "colors":colors
                    })
                    st.success(f"'{p_code}' 제품이 대기열에 추가되었습니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    # [탭 2] 생성 대기열
    with tab_queue:
        st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
        c_head, c_btn = st.columns([4, 1])
        with c_head: st.markdown(f"### 현재 대기 목록 ({len(st.session_state.product_list)}건)")
        with c_btn:
            if ui.button("목록 비우기", variant="outline", key="clear"):
                st.session_state.product_list = []
                st.rerun()
        
        if not st.session_state.product_list:
            st.info("대기 중인 항목이 없습니다. '정보 입력' 탭에서 제품을 추가해주세요.")
        else:
            for idx, item in enumerate(st.session_state.product_list):
                with st.expander(f"{idx+1}. {item['code']} - {item['name']}"):
                    cols = st.columns([1, 4])
                    cols[0].image(item['main_image'])
                    cols[1].write(f"컬러: {len(item['colors'])}개 | 로고: {item['logo']}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("PPT 생성 및 다운로드", type="primary"):
                ppt = create_pptx(st.session_state.product_list)
                st.download_button("PPT 파일 다운로드 (.pptx)", ppt, "BOSS_Golf_SpecSheet.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        st.markdown('</div>', unsafe_allow_html=True)


# 2.2 [페이지] 로고/아트워크 관리
elif selected_menu == '로고/아트워크 관리':
    st.title("자산 관리자 (Asset Manager)")
    st.markdown("PPT 제작에 사용될 로고와 아트워크 파일을 관리합니다.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 탭 메뉴 (한글화)
    active_tab = ui.tabs(options=['로고 (Logos)', '아트워크 (Artworks)'], defaultValue='로고 (Logos)', key="asset_tabs")
    target_dir = LOGO_DIR if '로고' in active_tab else ARTWORK_DIR
    
    # 1. 업로드 영역
    st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
    st.markdown(f"### 파일 업로드 ({active_tab})")
    uploaded = st.file_uploader("파일을 이곳에 끌어다 놓으세요", type=['png','jpg','svg'], accept_multiple_files=True)
    
    if uploaded and st.button("저장하기"):
        with st.spinner("서버 및 깃허브에 저장 중..."):
            for f in uploaded: upload_file(f, target_dir)
        st.success("저장이 완료되었습니다.")
        time.sleep(1)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 2. 갤러리 영역
    st.markdown('<div class="shadcn-card">', unsafe_allow_html=True)
    files = get_files(target_dir)
    st.markdown(f"### 보유 파일 목록 ({len(files)}개)")
    
    if not files:
        st.info("저장된 파일이 없습니다.")
    else:
        cols = st.columns(5)
        for i, f in enumerate(files):
            with cols[i%5]:
                st.image(os.path.join(target_dir, f), use_container_width=True)
                st.caption(f)
                # 삭제 버튼
                if st.button("삭제", key=f"del_{f}"):
                    delete_file_asset(f, target_dir)
                    time.sleep(1)
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)