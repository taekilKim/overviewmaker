import streamlit as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
import io
import os
import shutil # 파일 이동/이름변경용

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

# --- 세션 상태 초기화 ---
if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# --- 기능 로직: 파일 관리 ---
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
    
    # 확장자 유지
    ext = os.path.splitext(old_name)[1]
    if not new_name.endswith(ext):
        new_name += ext
        
    new_path = os.path.join(folder, new_name)
    
    if os.path.exists(new_path):
        return False, "이미 같은 이름의 파일이 존재합니다."
    
    os.rename(old_path, new_path)
    return True, "성공"

# --- 기능 로직: PPT 생성 ---
def create_pptx(products):
    if os.path.exists(TEMPLATE_FILE):
        prs = Presentation(TEMPLATE_FILE)
    else:
        prs = Presentation()

    for data in products:
        try:
            slide_layout = prs.slide_layouts[1] 
        except:
            slide_layout = prs.slide_layouts[0]
            
        slide = prs.slides.add_slide(slide_layout)

        # 1. 텍스트 정보
        textbox = slide.shapes.add_textbox(Inches(0.5), Inches(0.8), Inches(5), Inches(1))
        p = textbox.text_frame.paragraphs[0]
        p.text = f"{data['name']}\n{data['code']}"
        p.font.size = Pt(24)
        p.font.bold = True
        
        rrp_box = slide.shapes.add_textbox(Inches(7.5), Inches(0.8), Inches(2), Inches(0.5))
        rrp_box.text_frame.text = f"RRP : {data['rrp']}"
        rrp_box.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

        # 2. 이미지 배치
        if data['main_image']:
            slide.shapes.add_picture(data['main_image'], left=Inches(1.0), top=Inches(2.5), width=Inches(4.5))

        if data['logo'] and data['logo'] != "선택 없음":
            logo_path = os.path.join(LOGO_DIR, data['logo'])
            if os.path.exists(logo_path):
                slide.shapes.add_picture(logo_path, left=Inches(6.0), top=Inches(2.0), width=Inches(1.5))

        if data['artwork'] and data['artwork'] != "선택 없음":
            art_path = os.path.join(ARTWORK_DIR, data['artwork'])
            if os.path.exists(art_path):
                slide.shapes.add_picture(art_path, left=Inches(6.0), top=Inches(3.8), width=Inches(1.5))

        # 3. 컬러웨이
        start_x = 6.0
        start_y = 6.0
        img_width = 1.2
        gap = 0.3
        
        for i, color in enumerate(data['colors']):
            current_x = start_x + (i * (img_width + gap))
            if color['img']:
                slide.shapes.add_picture(color['img'], left=Inches(current_x), top=Inches(start_y), width=Inches(img_width))
            
            tb = slide.shapes.add_textbox(Inches(current_x), Inches(start_y + 1.3), Inches(img_width), Inches(0.4))
            p = tb.text_frame.paragraphs[0]
            p.text = color['name']
            p.font.size = Pt(9)
            p.alignment = PP_ALIGN.CENTER

    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output

# =========================================================
# 메인 어플리케이션 시작
# =========================================================
st.set_page_config(page_title="BOSS Spec Sheet Maker", layout="wide")
init_folders()

st.title("👕 BOSS 의류 스펙 시트 생성기")

# 상단 탭 네비게이션 생성
tab_main, tab_asset = st.tabs(["🛠️ PPT 제작 (Generator)", "📂 자산 관리 (Asset Manager)"])

# =========================================================
# 탭 1: PPT 제작 (기존 기능)
# =========================================================
with tab_main:
    col_input, col_list = st.columns([1, 2])
    
    # --- 좌측: 입력 폼 ---
    with col_input:
        st.subheader("1. 정보 입력")
        with st.form("add_product_form", clear_on_submit=True):
            prod_name = st.text_input("제품명", "MEN'S T-SHIRTS")
            prod_code = st.text_input("품번 (필수)", placeholder="예: BKFTM1581")
            prod_rrp = st.text_input("가격 (RRP)", "Undecided")
            main_img = st.file_uploader("메인 이미지", type=['png', 'jpg', 'jpeg'])
            
            # 자산 폴더에서 목록 실시간 로드
            logo_list = ["선택 없음"] + get_files(LOGO_DIR)
            art_list = ["선택 없음"] + get_files(ARTWORK_DIR)
            
            sel_logo = st.selectbox("로고 프리셋", logo_list)
            sel_artwork = st.selectbox("아트워크 프리셋", art_list)
            
            st.markdown("**컬러웨이 (최대 3개)**")
            c_data = []
            for i in range(3):
                cc1, cc2 = st.columns([1,2])
                with cc1:
                    ci = st.file_uploader(f"C{i+1} 사진", type=['png','jpg'], key=f"ci_{i}")
                with cc2:
                    cn = st.text_input(f"C{i+1} 이름", key=f"cn_{i}")
                if ci and cn: c_data.append({"img": ci, "name": cn})

            add_btn = st.form_submit_button("➕ 리스트에 추가")
            
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
                    st.success(f"{prod_code} 추가됨")

    # --- 우측: 리스트 및 생성 ---
    with col_list:
        st.subheader(f"2. 생성 대기 목록 ({len(st.session_state.product_list)}개)")
        
        if st.button("🗑️ 목록 전체 비우기"):
            st.session_state.product_list = []
            st.rerun()

        if len(st.session_state.product_list) == 0:
            st.info("좌측에서 정보를 입력하고 추가해주세요.")
        else:
            # 리스트 카드 형태로 보여주기
            for idx, item in enumerate(st.session_state.product_list):
                with st.container():
                    st.markdown(f"**{idx+1}. {item['code']}** | {item['name']}")
                    c1, c2 = st.columns([1, 6])
                    c1.image(item['main_image'], width=60)
                    c2.caption(f"Logo: {item['logo']} | Art: {item['artwork']} | Colors: {len(item['colors'])}개")
                    st.divider()

            if st.button("🚀 PPT 다운로드 (All Pages)", type="primary", use_container_width=True):
                ppt_io = create_pptx(st.session_state.product_list)
                st.download_button("📥 .pptx 파일 저장", ppt_io, "SpecSheet.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")

# =========================================================
# 탭 2: 자산 관리 (새로운 기능)
# =========================================================
with tab_asset:
    st.header("📂 자산 관리 매니저")
    st.info("PPT 제작 시 선택할 수 있는 로고와 아트워크 파일을 관리합니다.")
    
    # 1. 폴더 선택 (라디오 버튼)
    asset_type = st.radio("관리할 폴더 선택", ["Logos (로고)", "Artworks (아트워크)"], horizontal=True)
    target_dir = LOGO_DIR if asset_type == "Logos (로고)" else ARTWORK_DIR
    
    st.divider()

    # 2. 파일 업로드
    st.subheader("📤 파일 업로드")
    uploaded_files = st.file_uploader(f"{asset_type} 폴더에 추가할 이미지", type=['png', 'jpg'], accept_multiple_files=True)
    if uploaded_files:
        if st.button("서버에 저장하기"):
            for uf in uploaded_files:
                save_uploaded_file(uf, target_dir)
            st.success("저장 완료!")
            st.rerun()

    st.divider()

    # 3. 파일 목록 및 관리 (갤러리 형태)
    st.subheader(f"🖼️ 저장된 파일 목록 ({len(get_files(target_dir))}개)")
    
    files = get_files(target_dir)
    if not files:
        st.warning("저장된 파일이 없습니다.")
    else:
        # 그리드 형태로 배치 (한 줄에 4개씩)
        cols = st.columns(4)
        for i, file_name in enumerate(files):
            col = cols[i % 4]
            with col:
                file_path = os.path.join(target_dir, file_name)
                # (1) 미리보기 이미지
                st.image(file_path, use_container_width=True)
                
                # (2) 관리 기능 (Expander 안에 숨김)
                with st.expander(f"⚙️ {file_name}"):
                    # 이름 변경
                    new_name = st.text_input("새 이름", value=file_name, key=f"ren_{file_name}")
                    if st.button("이름 변경", key=f"btn_ren_{file_name}"):
                        if new_name != file_name:
                            success, msg = rename_file(target_dir, file_name, new_name)
                            if success:
                                st.success("변경 완료!")
                                st.rerun()
                            else:
                                st.error(msg)

                    # 삭제 기능
                    if st.button("🗑️ 삭제", key=f"btn_del_{file_name}", type="primary"):
                        delete_file(target_dir, file_name)
                        st.warning("삭제되었습니다.")
                        st.rerun()