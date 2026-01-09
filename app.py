import streamlit as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
import io
import os
from github import Github # 깃허브 연동 라이브러리

# --- 설정 ---
TEMPLATE_FILE = "template.pptx"
LOGO_DIR = "assets/logos"
ARTWORK_DIR = "assets/artworks"
CSS_FILE = "style.css"

# --- 깃허브 연동 함수 (핵심) ---
def upload_to_github(file_obj, folder_path):
    """
    파일을 받아서 GitHub 레포지토리에 직접 업로드(Commit)하는 함수
    """
    try:
        # Secrets에서 정보 가져오기
        token = st.secrets["github"]["token"]
        repo_name = st.secrets["github"]["repo_name"]
        branch = st.secrets["github"]["branch"]

        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # 깃허브 내의 파일 경로 (예: assets/logos/my_logo.png)
        file_path = f"{folder_path}/{file_obj.name}"
        
        # 파일 내용을 바이너리로 읽기
        content = file_obj.getvalue()

        try:
            # 이미 파일이 있는지 확인 (있으면 업데이트)
            contents = repo.get_contents(file_path, ref=branch)
            repo.update_file(file_path, f"Update {file_obj.name} via App", content, contents.sha, branch=branch)
            st.toast(f"🔄 기존 파일 업데이트 완료: {file_obj.name}")
        except:
            # 없으면 새로 생성
            repo.create_file(file_path, f"Upload {file_obj.name} via App", content, branch=branch)
            st.toast(f"✅ 새 파일 업로드 완료: {file_obj.name}")
            
        return True
    except Exception as e:
        st.error(f"GitHub 업로드 실패: {str(e)}")
        return False

def delete_from_github(filename, folder_path):
    """GitHub에서 파일 삭제"""
    try:
        token = st.secrets["github"]["token"]
        repo_name = st.secrets["github"]["repo_name"]
        branch = st.secrets["github"]["branch"]

        g = Github(token)
        repo = g.get_repo(repo_name)
        
        file_path = f"{folder_path}/{filename}"
        contents = repo.get_contents(file_path, ref=branch)
        repo.delete_file(file_path, f"Delete {filename} via App", contents.sha, branch=branch)
        st.toast(f"🗑️ 삭제 완료: {filename}")
        return True
    except Exception as e:
        st.error(f"삭제 실패: {str(e)}")
        return False

# --- 기타 유틸리티 ---
def init_folders():
    # 로컬에도 폴더는 있어야 에러가 안 남 (Streamlit이 Repo를 클론해오므로 기본적으로 있음)
    for folder in [LOGO_DIR, ARTWORK_DIR]:
        if not os.path.exists(folder):
            os.makedirs(folder)

def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_files(folder_path):
    if not os.path.exists(folder_path): return []
    return [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

# --- PPT 생성 로직 (동일) ---
def create_pptx(products):
    if os.path.exists(TEMPLATE_FILE): prs = Presentation(TEMPLATE_FILE)
    else: prs = Presentation()

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

        # 이미지 배치
        if data['main_image']:
            slide.shapes.add_picture(data['main_image'], left=Inches(1.0), top=Inches(2.5), width=Inches(4.5))
        
        # 로고 (assets 폴더에서 찾기)
        if data['logo'] and data['logo'] != "선택 없음":
            p_logo = os.path.join(LOGO_DIR, data['logo'])
            if os.path.exists(p_logo): 
                slide.shapes.add_picture(p_logo, left=Inches(6.0), top=Inches(2.0), width=Inches(1.5))
        
        # 아트워크
        if data['artwork'] and data['artwork'] != "선택 없음":
            p_art = os.path.join(ARTWORK_DIR, data['artwork'])
            if os.path.exists(p_art): 
                slide.shapes.add_picture(p_art, left=Inches(6.0), top=Inches(3.8), width=Inches(1.5))

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
# APP MAIN
# =========================================================
st.set_page_config(page_title="BOSS Admin", layout="wide", initial_sidebar_state="expanded")
init_folders()
load_css(CSS_FILE)

if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# --- 사이드바 ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Hugo_Boss_logo.svg/2560px-Hugo_Boss_logo.svg.png", width=120)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    menu = st.radio("MENU", ["홈 (Dashboard)", "스펙 시트 제작", "자산 관리"], label_visibility="collapsed")

# --- 콘텐츠 영역 ---

# 1. 홈
if "홈" in menu:
    st.title("Dashboard")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="content-card">
            <h3>대기 목록</h3>
            <h2 style="color:var(--toss-blue);">{len(st.session_state.product_list)}건</h2>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="content-card">
            <h3>등록된 로고</h3>
            <h2 style="color:var(--toss-blue);">{len(get_files(LOGO_DIR))}개</h2>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="content-card">
            <h3>등록된 아트워크</h3>
            <h2 style="color:var(--toss-blue);">{len(get_files(ARTWORK_DIR))}개</h2>
        </div>""", unsafe_allow_html=True)

# 2. 제작
elif "스펙" in menu:
    st.title("Spec Sheet Maker")
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    col_input, col_queue = st.columns([1, 1.2], gap="large")
    
    with col_input:
        st.subheader("제품 정보 입력")
        with st.form("main_form", clear_on_submit=True):
            st.caption("Basic Info")
            name = st.text_input("제품명", "MEN'S T-SHIRTS")
            code = st.text_input("품번 (필수)", placeholder="예: BKFTM1581")
            rrp = st.text_input("가격", "Undecided")
            
            st.caption("Design Resource")
            img = st.file_uploader("메인 이미지", type=['png','jpg'])
            # 파일 목록은 로컬 폴더(레포가 클론된 폴더)에서 읽어옴
            l_opt = ["선택 없음"] + get_files(LOGO_DIR)
            a_opt = ["선택 없음"] + get_files(ARTWORK_DIR)
            c1, c2 = st.columns(2)
            with c1: sl = st.selectbox("로고", l_opt)
            with c2: sa = st.selectbox("아트워크", a_opt)
            
            st.caption("Colorways (Max 3)")
            colors = []
            for i in range(3):
                cc1, cc2 = st.columns([1,2])
                with cc1: ci = st.file_uploader(f"img_{i}", type=['png','jpg'], key=f"c{i}", label_visibility="collapsed")
                with cc2: cn = st.text_input(f"nm_{i}", placeholder="색상명", key=f"n{i}", label_visibility="collapsed")
                if ci and cn: colors.append({"img":ci, "name":cn})
                st.write("")
            
            if st.form_submit_button("리스트 추가"):
                if not code or not img: st.error("품번과 이미지는 필수입니다.")
                else:
                    st.session_state.product_list.append({
                        "name":name, "code":code, "rrp":rrp, "main_image":img, 
                        "logo":sl, "artwork":sa, "colors":colors
                    })
                    st.success("추가됨")

    with col_queue:
        st.subheader(f"대기 목록 ({len(st.session_state.product_list)})")
        if st.button("목록 초기화"):
            st.session_state.product_list = []
            st.rerun()
            
        if not st.session_state.product_list:
            st.info("좌측에서 정보를 입력하세요.")
        else:
            for idx, item in enumerate(st.session_state.product_list):
                with st.expander(f"{idx+1}. {item['code']} - {item['name']}"):
                    st.caption(f"Colors: {len(item['colors'])}개 | Logo: {item['logo']}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("PPT 생성하기", type="primary"):
                ppt = create_pptx(st.session_state.product_list)
                st.download_button("다운로드", ppt, "Result.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
    st.markdown('</div>', unsafe_allow_html=True)

# 3. 자산 (깃허브 연동)
elif "자산" in menu:
    st.title("Asset Manager (GitHub Sync)")
    st.info("여기서 파일을 업로드하면 GitHub 저장소에 자동 저장되어 영구적으로 보관됩니다.")
    
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    c_sel, c_up = st.columns([1, 2])
    with c_sel:
        atype = st.radio("유형", ["Logos", "Artworks"])
        # 저장할 폴더 경로
        tdir = LOGO_DIR if atype == "Logos" else ARTWORK_DIR
    with c_up:
        upl = st.file_uploader("파일 업로드 (GitHub로 전송)", type=['png','jpg'], accept_multiple_files=True)
        if upl and st.button("저장하기"):
            with st.spinner("GitHub로 전송 중... (완료 후 앱이 새로고침 됩니다)"):
                success_count = 0
                for f in upl:
                    if upload_to_github(f, tdir):
                        success_count += 1
                
                if success_count > 0:
                    st.success(f"{success_count}개 파일 업로드 성공! 잠시 후 반영됩니다.")
                    # GitHub에 커밋하면 Streamlit Cloud가 알아서 감지하고 앱을 리부팅합니다.
                    # 따라서 수동 rerun이 필요 없을 수도 있지만, UX상 넣어줍니다.
                    import time
                    time.sleep(2)
                    st.rerun()
            
    st.markdown("---")
    fs = get_files(tdir)
    if not fs: st.warning("파일 없음")
    else:
        st.subheader(f"보유 파일 목록 ({len(fs)}개)")
        cols = st.columns(5)
        for i, f in enumerate(fs):
            with cols[i%5]:
                st.image(os.path.join(tdir, f), use_container_width=True)
                st.caption(f)
                if st.button("영구 삭제", key=f"d_{f}"):
                    if delete_from_github(f, tdir):
                        st.warning("삭제됨. 잠시 후 반영됩니다.")
                        import time
                        time.sleep(2)
                        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)