import streamlit as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
import io
import os

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

# 세션 상태 초기화 (새로고침 해도 리스트 유지)
if 'product_list' not in st.session_state:
    st.session_state.product_list = []

# --- PPT 생성 로직 ---
def create_pptx(products):
    if os.path.exists(TEMPLATE_FILE):
        prs = Presentation(TEMPLATE_FILE)
    else:
        prs = Presentation()

    for data in products:
        # 슬라이드 마스터의 1번 레이아웃(본문용) 사용 시도
        try:
            slide_layout = prs.slide_layouts[1] 
        except:
            slide_layout = prs.slide_layouts[0]
            
        slide = prs.slides.add_slide(slide_layout)

        # 1. 텍스트 정보
        # 제목 (좌측 상단)
        textbox = slide.shapes.add_textbox(Inches(0.5), Inches(0.8), Inches(5), Inches(1))
        p = textbox.text_frame.paragraphs[0]
        p.text = f"{data['name']}\n{data['code']}"
        p.font.size = Pt(24)
        p.font.bold = True
        
        # 가격 (우측 상단)
        rrp_box = slide.shapes.add_textbox(Inches(7.5), Inches(0.8), Inches(2), Inches(0.5))
        rrp_box.text_frame.text = f"RRP : {data['rrp']}"
        rrp_box.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

        # 2. 메인 이미지
        if data['main_image']:
            slide.shapes.add_picture(data['main_image'], left=Inches(1.0), top=Inches(2.5), width=Inches(4.5))

        # 3. 로고 (우측 박스)
        if data['logo'] and data['logo'] != "선택 없음":
            logo_path = os.path.join(LOGO_DIR, data['logo'])
            slide.shapes.add_picture(logo_path, left=Inches(6.0), top=Inches(2.0), width=Inches(1.5))

        # 4. 아트워크 (로고 아래 배치 예시)
        if data['artwork'] and data['artwork'] != "선택 없음":
            art_path = os.path.join(ARTWORK_DIR, data['artwork'])
            slide.shapes.add_picture(art_path, left=Inches(6.0), top=Inches(3.8), width=Inches(1.5))

        # 5. 컬러웨이 (하단)
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

# --- UI 시작 ---
st.set_page_config(page_title="BOSS Spec Sheet Maker (Multi)", layout="wide")
init_folders()

st.title("👕 BOSS 의류 스펙 시트 생성기 (멀티 페이지)")

# ==========================================
# 1. 사이드바: 자산 관리 및 입력 폼
# ==========================================
with st.sidebar:
    # [A] 자산 업로드 기능
    st.markdown("### 📂 자산 관리 (Assets)")
    with st.expander("로고/아트워크 업로드"):
        upload_type = st.radio("업로드 유형", ["Logos", "Artworks"])
        uploaded_asset = st.file_uploader("파일 선택", type=['png', 'jpg'])
        if uploaded_asset and st.button("파일 저장하기"):
            target_dir = LOGO_DIR if upload_type == "Logos" else ARTWORK_DIR
            save_path = os.path.join(target_dir, uploaded_asset.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_asset.getbuffer())
            st.success(f"{uploaded_asset.name} 저장 완료!")
            st.rerun() # 새로고침해서 목록 갱신

    st.markdown("---")
    
    # [B] 제품 정보 입력 폼
    st.markdown("### 📝 제품 정보 입력")
    # clear_on_submit=True를 써서 추가 후 폼을 비움
    with st.form("add_product_form", clear_on_submit=True):
        prod_name = st.text_input("제품명", "MEN'S T-SHIRTS")
        prod_code = st.text_input("품번 (필수)", placeholder="예: BKFTM1581")
        prod_rrp = st.text_input("가격 (RRP)", "Undecided")
        
        main_img = st.file_uploader("메인 이미지", type=['png', 'jpg', 'jpeg'])
        
        # 로고/아트워크 선택
        logo_list = ["선택 없음"] + get_files(LOGO_DIR)
        art_list = ["선택 없음"] + get_files(ARTWORK_DIR)
        
        sel_logo = st.selectbox("로고 선택", logo_list)
        sel_artwork = st.selectbox("아트워크 선택", art_list)
        
        st.write("🎨 컬러웨이 (최대 3개)")
        col1, col2, col3 = st.columns(3)
        colors_data = []
        
        # 컬러 1
        with col1:
            c1_img = st.file_uploader("C1 이미지", type=['png', 'jpg'])
            c1_name = st.text_input("C1 색상명")
        # 컬러 2
        with col2:
            c2_img = st.file_uploader("C2 이미지", type=['png', 'jpg'])
            c2_name = st.text_input("C2 색상명")
        # 컬러 3
        with col3:
            c3_img = st.file_uploader("C3 이미지", type=['png', 'jpg'])
            c3_name = st.text_input("C3 색상명")

        add_btn = st.form_submit_button("➕ 리스트에 추가")

        if add_btn:
            if not prod_code:
                st.error("품번은 필수입니다!")
            elif not main_img:
                st.error("메인 이미지를 넣어주세요!")
            else:
                # 컬러 데이터 정리
                if c1_img and c1_name: colors_data.append({"img": c1_img, "name": c1_name})
                if c2_img and c2_name: colors_data.append({"img": c2_img, "name": c2_name})
                if c3_img and c3_name: colors_data.append({"img": c3_img, "name": c3_name})
                
                # 세션에 저장 (메모리에 임시 저장)
                new_item = {
                    "name": prod_name,
                    "code": prod_code,
                    "rrp": prod_rrp,
                    "main_image": main_img,
                    "logo": sel_logo,
                    "artwork": sel_artwork,
                    "colors": colors_data
                }
                st.session_state.product_list.append(new_item)
                st.success(f"{prod_code} 추가됨! (현재 {len(st.session_state.product_list)}개)")

# ==========================================
# 2. 메인 화면: 리스트 확인 및 다운로드
# ==========================================
col_info, col_action = st.columns([3, 1])
with col_info:
    st.subheader(f"📋 생성 대기 목록 ({len(st.session_state.product_list)}개)")
with col_action:
    if st.button("🗑️ 목록 초기화"):
        st.session_state.product_list = []
        st.rerun()

if len(st.session_state.product_list) == 0:
    st.info("왼쪽 사이드바에서 제품 정보를 입력하고 '리스트에 추가' 버튼을 눌러주세요.")
else:
    # 리스트 보여주기
    for idx, item in enumerate(st.session_state.product_list):
        with st.expander(f"{idx+1}. {item['code']} - {item['name']}", expanded=False):
            c1, c2 = st.columns([1, 4])
            with c1:
                st.image(item['main_image'], width=100)
            with c2:
                st.write(f"**Logo:** {item['logo']} | **Artwork:** {item['artwork']}")
                st.write(f"**Colors:** {', '.join([c['name'] for c in item['colors']])}")

    st.divider()
    
    # 최종 생성 버튼
    if st.button("🚀 전체 슬라이드 PPT 생성하기", type="primary", use_container_width=True):
        with st.spinner("PPT 생성 중..."):
            ppt_file = create_pptx(st.session_state.product_list)
        
        st.success("생성 완료!")
        st.download_button(
            label="📥 PPT 파일 다운로드 (.pptx)",
            data=ppt_file,
            file_name="BOSS_Collection_SpecSheet.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )