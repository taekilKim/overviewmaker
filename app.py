import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit_antd_components as sac
from pptx import Presentation
from pptx.util import Mm, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.dml.color import RGBColor
from pptx.oxml.xmlchemy import OxmlElement
from pptx.oxml.ns import qn
import io
import os
import time
import math

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

# --- 텍스트 좌표/스타일 스펙 (mm 기준) ---
TEXT_SPECS = {
    "season": {
        "left": 20.43,
        "top": 10.24,
        "width": 83.33,
        "height": 9.49,
        "font_name": "Averta PE Extrabold",
        "font_size": 12,
        "bold": True,
        "color_hex": "#000000",  # 사용자 선택으로 덮어씀
    },
    "category": {
        "left": 6.94,
        "top": 21.92,
        "width": 117.05,
        "height": 13.85,
        "font_name": "Averta PE Extrabold",
        "font_size": 24,
        "bold": True,
        "color_hex": "#987147",
    },
    "code": {
        "left": 6.94,
        "top": 30.58,
        "width": 117.05,
        "height": 13.85,
        "font_name": "Averta PE Extrabold",
        "font_size": 24,
        "bold": True,
        "color_hex": "#000000",
    },
    "page": {
        "left": 9.53,
        "top": 12.49,
        "width": 15.53,
        "height": 4.00,
        "font_name": "Averta PE Light",
        "font_size": 9,
        "bold": False,
        "color_hex": "#987147",
    },
}

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

def get_layout_by_matching_name(prs, targets):
    target_set = {t.strip().lower() for t in targets}
    for layout in prs.slide_layouts:
        matching_name = (layout._element.get("matchingName") or "").strip().lower()
        if matching_name in target_set:
            return layout
    return None

def get_layout_by_name(prs, targets):
    target_set = {t.strip().lower() for t in targets}
    for layout in prs.slide_layouts:
        if (layout.name or "").strip().lower() in target_set:
            return layout
    return None

def get_text(shape):
    if not getattr(shape, "has_text_frame", False):
        return ""
    return (shape.text or "").strip()

def find_layout_anchor(layout):
    anchors = {}
    text_shapes = []
    empty_shapes = []

    for shp in layout.shapes:
        txt = get_text(shp)
        if txt:
            text_shapes.append(shp)
        elif getattr(shp, "shape_type", None) is not None:
            empty_shapes.append(shp)

    for shp in text_shapes:
        txt = get_text(shp).upper()
        if "LOGO" in txt:
            anchors["logo_label"] = shp
        if "ARTWORK" in txt:
            anchors["artwork_label"] = shp
        if "RRP" in txt:
            anchors["rrp_label"] = shp
        if "COLORWAY" in txt:
            anchors["color_label"] = shp

    # 텍스트 라벨 근처의 빈 도형을 이미지 박스로 사용
    def nearest_empty(label_key):
        label = anchors.get(label_key)
        if not label:
            return None
        lx = label.left + (label.width // 2)
        ly = label.top + (label.height // 2)
        candidates = []
        for shp in empty_shapes:
            w, h = shp.width, shp.height
            if w <= 0 or h <= 0:
                continue
            # 너무 작은 가이드/점은 제외
            if w < Mm(20) or h < Mm(10):
                continue
            sx = shp.left + (w // 2)
            sy = shp.top + (h // 2)
            dist = abs(sx - lx) + abs(sy - ly)
            candidates.append((dist, shp))
        return min(candidates, key=lambda x: x[0])[1] if candidates else None

    anchors["logo_box"] = nearest_empty("logo_label")
    anchors["artwork_box"] = nearest_empty("artwork_label")
    return anchors

def find_text_slot(layout, keywords):
    keyset = [k.upper() for k in keywords]
    for shp in layout.shapes:
        txt = get_text(shp).upper()
        if not txt:
            continue
        if any(k in txt for k in keyset):
            return shp
    return None

def hex_to_rgbcolor(hex_color):
    if not hex_color:
        return None
    v = hex_color.strip().lstrip("#")
    if len(v) != 6:
        return None
    try:
        return RGBColor(int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
    except:
        return None

def replace_text_in_slide(slide, tokens, value, color_override=None):
    token_set = [t.upper() for t in tokens]
    for shp in slide.shapes:
        if not getattr(shp, "has_text_frame", False):
            continue
        current = (shp.text or "")
        up = current.upper()
        if any(t in up for t in token_set):
            style = extract_text_style(shp)
            shp.text_frame.clear()
            shp.text_frame.text = value
            p = shp.text_frame.paragraphs[0]
            apply_text_style(p, style)
            if color_override is not None:
                try:
                    p.font.color.rgb = color_override
                except:
                    pass
            return True
    return False

def extract_text_style(shape):
    style = {"align": None, "size": None, "bold": None, "italic": None, "name": None, "color_rgb": None}
    if not getattr(shape, "has_text_frame", False):
        return style
    tf = shape.text_frame
    if not tf.paragraphs:
        return style
    p = tf.paragraphs[0]
    style["align"] = p.alignment
    f = p.font
    style["size"] = f.size
    style["bold"] = f.bold
    style["italic"] = f.italic
    style["name"] = f.name
    try:
        if f.color and getattr(f.color, "rgb", None):
            style["color_rgb"] = f.color.rgb
    except:
        pass
    return style

def apply_text_style(paragraph, style):
    if style.get("align") is not None:
        paragraph.alignment = style["align"]
    f = paragraph.font
    if style.get("size") is not None:
        f.size = style["size"]
    if style.get("bold") is not None:
        f.bold = style["bold"]
    if style.get("italic") is not None:
        f.italic = style["italic"]
    if style.get("name"):
        f.name = style["name"]
    if style.get("color_rgb") is not None:
        try:
            f.color.rgb = style["color_rgb"]
        except:
            pass

def add_styled_textbox(slide, slot_shape, text, fallback_left, fallback_top, fallback_w, fallback_h, fallback_size):
    if slot_shape is not None:
        tb = slide.shapes.add_textbox(slot_shape.left, slot_shape.top, slot_shape.width, slot_shape.height)
        style = extract_text_style(slot_shape)
    else:
        tb = slide.shapes.add_textbox(fallback_left, fallback_top, fallback_w, fallback_h)
        style = {"size": fallback_size, "bold": True}
    tb.text_frame.text = text
    p = tb.text_frame.paragraphs[0]
    apply_text_style(p, style)
    return tb

def add_text_by_spec(slide, text, spec, color_override=None):
    tb = slide.shapes.add_textbox(
        Mm(spec["left"]),
        Mm(spec["top"]),
        Mm(spec["width"]),
        Mm(spec["height"]),
    )
    tf = tb.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    f = run.font
    f.name = spec["font_name"]
    f.size = Pt(spec["font_size"])
    f.bold = spec.get("bold")

    # 일부 PowerPoint 환경에서 font.name만으로는 폰트 유지가 불안정해서
    # run 레벨의 latin/ea/cs 타입페이스를 함께 강제 지정한다.
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:ea", "a:cs"):
        node = rPr.find(qn(tag))
        if node is None:
            node = OxmlElement(tag)
            rPr.append(node)
        node.set("typeface", spec["font_name"])

    color = color_override or spec.get("color_hex")
    rgb = hex_to_rgbcolor(color)
    if rgb is not None:
        try:
            f.color.rgb = rgb
        except:
            pass
    return tb

def has_slide_number_placeholder(slide):
    for shp in slide.shapes:
        if not getattr(shp, "is_placeholder", False):
            continue
        try:
            if shp.placeholder_format.type == PP_PLACEHOLDER.SLIDE_NUMBER:
                return True
        except:
            continue
    return False

def strip_vendor_watermark(prs):
    markers = ("VORLAGENBAUER", "ERSTELLT DURCH")
    targets = list(prs.slide_masters)
    for m in prs.slide_masters:
        targets.extend(list(m.slide_layouts))

    for container in targets:
        for shp in container.shapes:
            if not getattr(shp, "has_text_frame", False):
                continue
            txt = (shp.text or "").upper()
            if any(marker in txt for marker in markers):
                shp.text_frame.clear()

# --- 깃허브 연동 ---
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
    strip_vendor_watermark(prs)

    # 레이아웃 선택 우선순위:
    # 1) matchingName = default (요청사항 우선)
    # 2) matchingName = title
    # 3) 표시 이름 = HB Title / Content, CUSTOM
    # 3) 기존 인덱스 폴백
    selected_layout = (
        get_layout_by_matching_name(prs, ["default"])
        or get_layout_by_matching_name(prs, ["title"])
        or get_layout_by_name(prs, ["HB Title / Content", "CUSTOM"])
    )
    if selected_layout is None:
        selected_layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
    layout_anchors = find_layout_anchor(selected_layout)

    base_slide_count = len(prs.slides)

    for idx, data in enumerate(products):
        slide = prs.slides.add_slide(selected_layout)
        page_no = base_slide_count + idx + 1
        season_color_hex = data.get("season_color") or TEXT_SPECS["season"]["color_hex"]

        # 텍스트: 좌표 고정 매핑
        season_name = data.get("season_item", "")
        if season_name:
            add_text_by_spec(
                slide,
                season_name,
                TEXT_SPECS["season"],
                color_override=season_color_hex,
            )

        add_text_by_spec(
            slide,
            data["name"],
            TEXT_SPECS["category"],
        )
        add_text_by_spec(
            slide,
            data["code"],
            TEXT_SPECS["code"],
        )

        add_text_by_spec(
            slide,
            f"PAGE {page_no}",
            TEXT_SPECS["page"],
        )
        
        # RRP (표시만 함)
        if data.get('rrp'):
            rrp_left = layout_anchors["rrp_label"].left if layout_anchors.get("rrp_label") else Mm(250)
            rrp_top = layout_anchors["rrp_label"].top if layout_anchors.get("rrp_label") else Mm(15)
            rrp = slide.shapes.add_textbox(rrp_left, rrp_top, Mm(50), Mm(15))
            rrp.text_frame.text = f"RRP : {data['rrp']}"
            rrp.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

        # 메인 이미지
        if data['main_image']:
            slide.shapes.add_picture(data['main_image'], left=Mm(20), top=Mm(60), width=Mm(140))
        
        # 로고
        if data['logo'] and data['logo'] != "선택 없음":
            p_logo = os.path.join(LOGO_DIR, data['logo'])
            if os.path.exists(p_logo):
                if layout_anchors.get("logo_box"):
                    box = layout_anchors["logo_box"]
                    slide.shapes.add_picture(p_logo, left=box.left, top=box.top, width=box.width, height=box.height)
                else:
                    slide.shapes.add_picture(p_logo, left=Mm(180), top=Mm(60), width=Mm(40))
        
        # 아트워크 (첫 번째 선택된 것 배치)
        if data['artworks']:
            first_art = data['artworks'][0]
            p_art = os.path.join(ARTWORK_DIR, first_art)
            if os.path.exists(p_art):
                if layout_anchors.get("artwork_box"):
                    box = layout_anchors["artwork_box"]
                    slide.shapes.add_picture(p_art, left=box.left, top=box.top, width=box.width, height=box.height)
                else:
                    slide.shapes.add_picture(p_art, left=Mm(180), top=Mm(110), width=Mm(40))

        # 컬러웨이
        sx, sy, w, g = 180, 155, 30, 5
        if layout_anchors.get("color_label"):
            # 라벨 아래 우하단 영역을 시작점으로 사용
            sx = layout_anchors["color_label"].left / 36000.0
            sy = 155
        per_row = 3
        row_gap = 8
        img_h = 30
        rows = max(1, math.ceil(len(data['colors']) / per_row)) if data.get('colors') else 1
        for i, c in enumerate(data['colors']):
            row = i // per_row
            col = i % per_row
            # 2줄 이상이면 아래줄 고정 후 위로 쌓기
            cy = sy - (rows - 1 - row) * (img_h + row_gap + 10)
            cx = sx + (col * (w + g))
            if c['img']:
                slide.shapes.add_picture(c['img'], left=Mm(cx), top=Mm(cy), width=Mm(w))
            tb = slide.shapes.add_textbox(Mm(cx), Mm(cy + img_h + 2), Mm(w), Mm(10))
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

# --- 1. 좌측 사이드바 ---
with st.sidebar:
    if os.path.exists(SIDEBAR_LOGO):
        st.image(SIDEBAR_LOGO, width=140)
    else:
        st.header("BOSS Golf")
    
    st.markdown("---")

    selected_menu = sac.menu([
        sac.MenuItem('슬라이드 제작', icon='file-earmark-plus'),
        sac.MenuItem('로고&아트워크 관리', icon='image'),
    ], size='sm', color='dark', open_all=True)

    # [수정] 깃허브 연동 상태 표시 제거됨


# --- 2. 메인 콘텐츠 ---

if selected_menu == '슬라이드 제작':
    st.title("슬라이드 제작")
    st.markdown("제품 정보를 입력하여 스펙 시트를 생성합니다.")
    st.markdown("---")

    tab_editor, tab_queue = st.tabs(["정보 입력", "생성 대기열"])
    
    # 탭 1: 입력
    with tab_editor:
        # 폼 시작
        with st.form("spec_form", clear_on_submit=False):
            st.subheader("1. 기본 정보")
            c1, c2 = st.columns([3, 1])
            with c1:
                season_item = st.text_input("시즌 아이템명", "JETSET LUXE")
                season_color = st.color_picker("시즌 텍스트 색상", "#000000")
                p_name = st.text_input("제품명", "MEN'S T-SHIRTS")
                p_code = st.text_input("품번 (필수)", placeholder="예: BKFTM1581")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("2. 디자인 자산")
            
            # 메인 이미지
            main_img = st.file_uploader("메인 이미지", type=['png','jpg'], help="슬라이드 좌측에 크게 들어갈 이미지")
            
            c3, c4 = st.columns(2)
            with c3:
                s_logo = st.selectbox("로고 선택", ["선택 없음"] + get_files(LOGO_DIR))
            
            with c4:
                # 아트워크 다중 선택 (Popover)
                available_artworks = get_files(ARTWORK_DIR)
                selected_artworks = []
                
                with st.popover("아트워크 선택하기", use_container_width=True):
                    if not available_artworks:
                        st.warning("등록된 아트워크가 없습니다.")
                    else:
                        for art in available_artworks:
                            ac1, ac2 = st.columns([1, 4])
                            with ac1:
                                is_checked = st.checkbox("V", key=f"chk_{art}", label_visibility="hidden")
                            with ac2:
                                st.image(os.path.join(ARTWORK_DIR, art), width=40)
                                st.caption(art)
                            if is_checked:
                                selected_artworks.append(art)
                
                if selected_artworks:
                    st.caption(f"선택됨: {', '.join(selected_artworks)}")
                else:
                    st.caption("선택된 아트워크 없음")

            st.markdown("---")
            st.subheader("3. 컬러웨이 (Colorways)")
            
            # 일괄 업로드
            uploaded_colors = st.file_uploader("컬러웨이 이미지 일괄 업로드 (최대 4개)", type=['png','jpg'], accept_multiple_files=True)
            colors_input = []
            
            if uploaded_colors:
                st.info(f"{len(uploaded_colors)}개의 이미지가 선택되었습니다. 색상명을 입력해주세요.")
                for idx, c_file in enumerate(uploaded_colors[:4]):
                    col_card, col_input = st.columns([1, 4])
                    with col_card:
                        st.image(c_file, width=60)
                    with col_input:
                        c_name = st.text_input(f"색상명 {idx+1}", key=f"c_name_{idx}")
                    colors_input.append({"img": c_file, "name": c_name})
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 제출
            if st.form_submit_button("대기열에 추가", type="primary"):
                if not p_code or not main_img:
                    st.error("품번과 메인 이미지는 필수입니다.")
                else:
                    st.session_state.product_list.append({
                        "season_item": season_item,
                        "season_color": season_color,
                        "name":p_name, "code":p_code, "rrp":"", 
                        "main_image":main_img, 
                        "logo":s_logo, 
                        "artworks": selected_artworks,
                        "artwork": selected_artworks[0] if selected_artworks else "선택 없음",
                        "colors": colors_input
                    })
                    st.success(f"'{p_code}' 추가 완료!")

    # 탭 2: 대기열
    with tab_queue:
        c_head, c_btn = st.columns([4, 1])
        with c_head: st.subheader(f"생성 대기 목록 ({len(st.session_state.product_list)})")
        with c_btn:
            if st.button("목록 비우기"):
                st.session_state.product_list = []
                st.rerun()
        
        if not st.session_state.product_list:
            st.info("대기 중인 항목이 없습니다.")
        else:
            for idx, item in enumerate(st.session_state.product_list):
                with st.expander(f"{idx+1}. {item['code']} - {item['name']}"):
                    cols = st.columns([1, 4])
                    cols[0].image(item['main_image'])
                    art_str = ", ".join(item['artworks']) if item.get('artworks') else "-"
                    cols[1].write(f"컬러: {len(item['colors'])}개 | 로고: {item['logo']} | 아트워크: {art_str}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("PPT 생성 및 다운로드", type="primary"):
                try:
                    ppt = create_pptx(st.session_state.product_list)
                    st.download_button("PPT 다운로드 (.pptx)", ppt, "BOSS_Golf_SpecSheet.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
                except Exception as e:
                    st.error(f"PPT 생성 실패: {e}")


elif selected_menu == '로고&아트워크 관리':
    st.title("자산 관리")
    st.markdown("디자인 자산을 업로드하고 관리합니다.")
    st.markdown("---")
    
    active_tab = ui.tabs(options=['로고', '아트워크'], defaultValue='로고', key="asset_tabs")
    target_dir = LOGO_DIR if active_tab == '로고' else ARTWORK_DIR
    
    st.subheader(f"{active_tab} 업로드")
    uploaded = st.file_uploader("파일 업로드", type=['png','jpg','svg'], accept_multiple_files=True)
    if uploaded and st.button("저장하기"):
        with st.spinner("저장 중..."):
            for f in uploaded: upload_file(f, target_dir)
        st.success("완료")
        time.sleep(1)
        st.rerun()
    
    st.markdown("---")
    st.subheader("보유 파일 목록")
    files = get_files(target_dir)
    
    if not files:
        st.info("파일이 없습니다.")
    else:
        cols = st.columns(5)
        for i, f in enumerate(files):
            with cols[i%5]:
                st.image(os.path.join(target_dir, f), use_container_width=True)
                st.caption(f)
                if st.button("삭제", key=f"del_{f}"):
                    delete_file_asset(f, target_dir)
                    time.sleep(1)
                    st.rerun()
