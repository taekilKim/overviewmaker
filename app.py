import streamlit as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
import io
import os

# --- 설정: 기본 폰트나 색상 등을 여기서 설정 ---
# PPT 템플릿 파일명
TEMPLATE_FILE = "template.pptx"
# 에셋(로고) 폴더 경로
ASSETS_DIR = "assets"

def init_layout():
    st.set_page_config(page_title="BOSS Spec Sheet Maker", layout="wide")
    st.title("👕 BOSS 의류 스펙 시트 생성기")
    st.markdown("---")

def get_asset_files():
    """assets 폴더에서 이미지 파일 목록을 가져옵니다."""
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
        return []
    return [f for f in os.listdir(ASSETS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

def create_pptx(data):
    """입력된 데이터를 바탕으로 PPT를 생성합니다."""
    
    # 1. 템플릿 로드 (없으면 기본 빈 PPT 생성)
    if os.path.exists(TEMPLATE_FILE):
        prs = Presentation(TEMPLATE_FILE)
    else:
        prs = Presentation() # 템플릿 없으면 백지 시작

    # 2. 슬라이드 추가 (템플릿의 첫 번째 레이아웃 사용)
    # 보통 0번은 제목슬라이드, 1번이 빈 슬라이드인 경우가 많음. 필요시 숫자 조정.
    # 디자인이 이미 되어있는 슬라이드 하나를 복사해서 쓰고 싶다면 로직이 달라지지만,
    # 여기서는 '빈 레이아웃'에 '이미지'를 얹는 방식을 씁니다.
    slide_layout = prs.slide_layouts[0] 
    slide = prs.slides.add_slide(slide_layout)

    # --- A. 텍스트 정보 배치 ---
    # 제품명 (좌측 상단)
    textbox = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(5), Inches(1))
    tf = textbox.text_frame
    p = tf.paragraphs[0]
    p.text = f"{data['name']}\n{data['code']}"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.name = 'Arial' # 폰트 지정 가능

    # 가격 (우측 상단)
    rrp_box = slide.shapes.add_textbox(Inches(7.5), Inches(0.5), Inches(2), Inches(0.5))
    rrp_box.text_frame.text = f"RRP : {data['rrp']}"

    # --- B. 메인 이미지 배치 (좌측 메인) ---
    if data['main_image']:
        # 위치: 왼쪽 1.0인치, 위쪽 2.5인치, 너비 4.5인치
        slide.shapes.add_picture(data['main_image'], left=Inches(1.0), top=Inches(2.5), width=Inches(4.5))

    # --- C. 로고/아트워크 배치 (우측 박스) ---
    # 선택된 로고가 있다면
    if data['logo_file']:
        logo_path = os.path.join(ASSETS_DIR, data['logo_file'])
        # 위치: 왼쪽 6.5인치, 위쪽 2.5인치, 너비 2.0인치
        slide.shapes.add_picture(logo_path, left=Inches(6.5), top=Inches(2.5), width=Inches(2.0))

    # --- D. 컬러웨이 배치 (우측 하단) ---
    # 시작 좌표
    start_x = 6.5
    start_y = 5.5
    img_width = 1.5
    gap = 0.2  # 간격

    # 사용자가 입력한 컬러 리스트 반복
    for i, color in enumerate(data['colors']):
        # 현재 위치 계산
        current_x = start_x + (i * (img_width + gap))
        
        # 1. 작은 옷 이미지
        if color['img']:
            slide.shapes.add_picture(color['img'], left=Inches(current_x), top=Inches(start_y), width=Inches(img_width))
        
        # 2. 색상 이름 텍스트
        tb = slide.shapes.add_textbox(Inches(current_x), Inches(start_y - 0.4), Inches(img_width), Inches(0.4))
        p = tb.text_frame.paragraphs[0]
        p.text = color['name']
        p.font.size = Pt(10)
        p.alignment = PP_ALIGN.CENTER

    # --- E. 저장 (메모리 스트림) ---
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output

def main():
    init_layout()
    
    # --- UI: 왼쪽(입력) / 오른쪽(설명) ---
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("1. 기본 정보 입력")
        prod_name = st.text_input("제품명 (Product Name)", "MEN'S T-SHIRTS _SEA LINE")
        prod_code = st.text_input("품번 (Product Code)", "BKFTM1581")
        prod_rrp = st.text_input("가격 (RRP)", "Undecided")

        st.subheader("2. 메인 이미지")
        main_img = st.file_uploader("큰 옷 이미지 업로드", type=['png', 'jpg', 'jpeg'])

        st.subheader("3. 로고 & 아트워크 (Preset)")
        assets = get_asset_files()
        if assets:
            selected_logo = st.selectbox("적용할 로고/아트워크 선택", ["선택안함"] + assets)
        else:
            st.warning("assets 폴더에 이미지가 없습니다.")
            selected_logo = "선택안함"

        st.subheader("4. 컬러웨이 (Colorways)")
        # 컬러웨이 입력을 위한 컨테이너
        colors_input = []
        # 3칸을 나란히 만듦
        cols = st.columns(3)
        for i, col in enumerate(cols):
            with col:
                st.markdown(f"**Color {i+1}**")
                c_name = st.text_input(f"색상명", key=f"cn_{i}")
                c_img = st.file_uploader(f"이미지", type=['png', 'jpg'], key=f"ci_{i}")
                if c_name and c_img:
                    colors_input.append({"name": c_name, "img": c_img})

    with col2:
        st.info("💡 사용법\n\n1. 왼쪽 폼을 채우세요.\n2. 'assets' 폴더에 로고 이미지를 넣어두면 목록에 뜹니다.\n3. 아래 버튼을 누르면 PPT가 다운로드됩니다.")
        
        st.markdown("### 미리보기 (Preview)")
        if main_img:
            st.image(main_img, caption="메인 이미지", width=300)
        else:
            st.write("이미지를 올리면 여기에 미리보기가 뜹니다.")

    st.markdown("---")
    
    # 생성 버튼
    if st.button("🚀 스펙 시트 생성하기 (PPT 다운로드)", type="primary", use_container_width=True):
        if not main_img:
            st.error("메인 이미지는 필수입니다!")
            return

        # 데이터 패키징
        input_data = {
            "name": prod_name,
            "code": prod_code,
            "rrp": prod_rrp,
            "main_image": main_img,
            "logo_file": None if selected_logo == "선택안함" else selected_logo,
            "colors": colors_input
        }

        # PPT 생성 함수 호출
        try:
            ppt_file = create_pptx(input_data)
            
            st.success("생성 완료! 버튼을 눌러 저장하세요.")
            st.download_button(
                label="📥 PPT 파일 다운로드",
                data=ppt_file,
                file_name=f"{prod_code}_SpecSheet.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
