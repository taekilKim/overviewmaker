import streamlit as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
import io
import os
from PIL import Image

# --- 설정 ---
TEMPLATE_FILE = "template.pptx"
ASSETS_DIR = "assets"

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="BOSS Spec Sheet Maker", layout="wide")

# CSS로 미리보기 영역을 하얀색 A4 용지처럼 보이게 꾸밈
st.markdown("""
<style>
    .preview-container {
        background-color: white;
        padding: 20px;
        border: 1px solid #ddd;
        border-radius: 5px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        color: black;
    }
    .preview-header { font-size: 24px; font-weight: bold; margin-bottom: 5px; color: #000; }
    .preview-sub { font-size: 14px; color: #555; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("👕 BOSS 의류 스펙 시트 생성기 (Pro)")

# --- 2. 로직 함수 ---
def get_asset_files():
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
        return []
    return [f for f in os.listdir(ASSETS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

def create_pptx(data_list):
    """
    data_list: 슬라이드 데이터들이 담긴 리스트 (다중 페이지 지원)
    """
    if os.path.exists(TEMPLATE_FILE):
        prs = Presentation(TEMPLATE_FILE)
    else:
        prs = Presentation() # 템플릿 없으면 깡통 생성

    # 입력된 데이터만큼 반복해서 슬라이드 추가
    for data in data_list:
        # [중요] 템플릿의 레이아웃 선택 (보통 0:제목, 1:본문... 템플릿마다 다름)
        # 사용자가 만든 마스터 슬라이드 중 '본문용' 레이아웃을 1번이라고 가정
        try:
            slide_layout = prs.slide_layouts[1] 
        except:
            slide_layout = prs.slide_layouts[0] # 실패하면 0번 사용
            
        slide = prs.slides.add_slide(slide_layout)

        # (A) 텍스트 정보
        # 제목 박스 생성 (위치: 좌측 상단)
        textbox = slide.shapes.add_textbox(Inches(0.5), Inches(0.8), Inches(5), Inches(1))
        tf = textbox.text_frame
        p = tf.paragraphs[0]
        p.text = f"{data['name']}\n{data['code']}"
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.name = 'Arial'

        # 가격 (우측 상단)
        rrp_box = slide.shapes.add_textbox(Inches(7.5), Inches(0.8), Inches(2), Inches(0.5))
        rrp_box.text_frame.text = f"RRP : {data['rrp']}"
        rrp_box.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

        # (B) 메인 이미지
        if data['main_image']:
            # Streamlit UploadedFile 객체를 BytesIO로 변환 없이 바로 사용 가능
            slide.shapes.add_picture(data['main_image'], left=Inches(1.0), top=Inches(2.5), width=Inches(4.5))

        # (C) 로고
        if data['logo_file']:
            logo_path = os.path.join(ASSETS_DIR, data['logo_file'])
            slide.shapes.add_picture(logo_path, left=Inches(6.5), top=Inches(2.5), width=Inches(2.0))

        # (D) 컬러웨이
        start_x = 6.5
        start_y = 5.5
        img_width = 1.2
        gap = 0.3
        
        for i, color in enumerate(data['colors']):
            current_x = start_x + (i * (img_width + gap))
            # 이미지
            if color['img']:
                slide.shapes.add_picture(color['img'], left=Inches(current_x), top=Inches(start_y), width=Inches(img_width))
            # 텍스트
            tb = slide.shapes.add_textbox(Inches(current_x), Inches(start_y + 1.3), Inches(img_width), Inches(0.4))
            p = tb.text_frame.paragraphs[0]
            p.text = color['name']
            p.font.size = Pt(9)
            p.alignment = PP_ALIGN.CENTER

    # 저장
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output

# --- 3. UI 구성 (사이드바 입력 / 메인 미리보기) ---

# (1) 사이드바: 입력 폼 (st.form 사용 -> 새로고침 방지!)
with st.sidebar:
    st.header("📝 정보 입력")
    with st.form("spec_form", clear_on_submit=False):
        prod_name = st.text_input("제품명", "MEN'S T-SHIRTS _SEA LINE")
        prod_code = st.text_input("품번", "BKFTM1581")
        prod_rrp = st.text_input("가격 (RRP)", "Undecided")
        
        st.markdown("---")
        st.write("🖼️ 이미지 업로드")
        main_img = st.file_uploader("메인 이미지", type=['png', 'jpg', 'jpeg'])
        
        assets = get_asset_files()
        selected_logo = st.selectbox("로고 선택 (assets폴더)", ["선택안함"] + assets) if assets else "선택안함"
        
        st.markdown("---")
        st.write("🎨 컬러웨이 (최대 3개)")
        
        # 컬러웨이 입력을 리스트로 관리
        c_inputs = []
        for i in range(3):
            c_col1, c_col2 = st.columns([1, 2])
            with c_col1:
                c_img = st.file_uploader(f"컬러 {i+1} 이미지", type=['png', 'jpg'], key=f"img_{i}")
            with c_col2:
                c_name = st.text_input(f"컬러 {i+1} 이름", key=f"name_{i}")
            
            if c_img and c_name:
                c_inputs.append({"name": c_name, "img": c_img})

        submitted = st.form_submit_button("✅ 미리보기 업데이트 & 적용")

# (2) 메인 화면: 실시간 미리보기 (HTML/Layout 이용)
st.subheader("🖥️ 슬라이드 미리보기 (예상)")

# 데이터 패키징
current_data = {
    "name": prod_name,
    "code": prod_code,
    "rrp": prod_rrp,
    "main_image": main_img,
    "logo_file": None if selected_logo == "선택안함" else selected_logo,
    "colors": c_inputs
}

# --- 미리보기 렌더링 (PPT가 아니라 웹 화면으로 흉내내기) ---
with st.container():
    # 하얀색 박스 안에서 레이아웃 구성
    st.markdown('<div class="preview-container">', unsafe_allow_html=True)
    
    # 상단 (제목 + 가격)
    p_col1, p_col2 = st.columns([3, 1])
    with p_col1:
        st.markdown(f'<div class="preview-header">{current_data["name"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="preview-sub">{current_data["code"]}</div>', unsafe_allow_html=True)
    with p_col2:
        st.markdown(f'<div style="text-align:right; font-weight:bold;">RRP : {current_data["rrp"]}</div>', unsafe_allow_html=True)
    
    st.markdown("---") # 구분선

    # 중단 (메인 이미지 + 우측 정보)
    m_col1, m_col2 = st.columns([1.5, 1])
    
    with m_col1: # 왼쪽: 메인 이미지
        if current_data['main_image']:
            st.image(current_data['main_image'], width=400)
        else:
            st.info("메인 이미지를 업로드하세요.")
            
    with m_col2: # 오른쪽: 로고 + 컬러웨이
        # 로고
        if current_data['logo_file']:
            st.image(os.path.join(ASSETS_DIR, current_data['logo_file']), width=150, caption="Logo")
        else:
            st.empty() # 공간만 차지
            
        st.markdown("<br><br>", unsafe_allow_html=True) # 여백
        
        # 컬러웨이
        if current_data['colors']:
            st.write("**Colorways**")
            c_cols = st.columns(len(current_data['colors']))
            for idx, c in enumerate(current_data['colors']):
                with c_cols[idx]:
                    st.image(c['img'], use_container_width=True)
                    st.caption(c['name'])
        else:
            st.write("(컬러웨이 정보 없음)")

    st.markdown('</div>', unsafe_allow_html=True)

# --- 4. 최종 PPT 생성 버튼 ---
st.divider()
if st.button("📥 PPT 파일 생성 및 다운로드", type="primary"):
    if not current_data['main_image']:
        st.error("⚠️ 메인 이미지가 없으면 생성할 수 없습니다.")
    else:
        # 리스트 형태로 넘김 (나중에 여러 제품 추가 기능 확장을 위해)
        ppt_file = create_pptx([current_data])
        
        st.success("생성 완료!")
        st.download_button(
            label="PPT 다운로드 시작",
            data=ppt_file,
            file_name=f"{prod_code}_SpecSheet.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )