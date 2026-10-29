import streamlit as st
import xml.etree.ElementTree as ET
import re
import os
from collections import defaultdict

def clean_name_symbols(text):
    """씨수말 이름 맨 앞의 숫자, 특수기호(도형, 기호 등), 공백을 모두 제거합니다."""
    cleaned = re.sub(r'^[\d\s\W_]+', '', text)
    return cleaned.strip()

def normalize_name(text):
    """이름 정제 및 비교용 표준화"""
    clean = text.replace('@', '').replace('#', '').replace('*', '')
    clean = clean.replace('＠', '').replace('＃', '')
    clean = clean.replace('암)', '').replace('수)', '').replace('거)', '')
    clean = clean.replace('가.', '').replace('나.', '').replace('다.', '')
    clean = clean.split('(')[0]
    return clean.strip().lower()

# 1. 페이지 설정
st.set_page_config(page_title="씨수말 & 외조부마(BMS) 통합 혈통 닉 분석기", layout="wide")

# CSS 스타일 정의
st.markdown("""
    <style>
    .elite-mare {
        color: #0077CC !important;
        font-weight: bold;
        font-size: 1.25em;
        margin-top: 15px;
        margin-bottom: 6px;
    }
    .progeny-item {
        margin-left: 25px;
        margin-bottom: 5px;
        color: #333333;
        font-size: 1.05em;
    }
    .premium-progeny {
        color: #D32F2F !important;
        font-weight: bold;
    }
    /* 암말 @, #, * 기호 진한 파란색 강조 */
    .highlight-elite-daughter {
        color: #0000FF !important;
        font-weight: 900 !important;
    }
    /* 수말 G1-7두 이상 진한 파란색 강조 */
    .highlight-g1-son {
        color: #0000FF !important;
        font-weight: 900 !important;
    }
    .star-daughter {
        color: #000000 !important;
        font-weight: 900 !important;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .section-title {
        color: #111111;
        font-weight: bold;
        font-size: 1.3em;
        margin-top: 15px;
        margin-bottom: 6px;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_mindmap_data():
    """xml/mm 파일 전체 노드 데이터 및 parent-child 맵핑 데이터 로드"""
    file_path = '우수한 경주마(수말, 암말).mm'
    if not os.path.exists(file_path):
        return None, None, None, None, f"'{file_path}' 파일을 찾을 수 없습니다."
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
            if not content:
                return None, None, None, None, f"'{file_path}' 파일의 내용이 비어 있습니다."
            root = ET.fromstring(content)
        
        id_to_text = {}
        id_to_parent_text = {}
        id_to_node = {}
        
        for parent in root.iter('node'):
            p_text = parent.get('TEXT', 'Unknown')
            for child in parent.findall('node'):
                c_id = child.get('ID')
                if c_id:
                    id_to_text[c_id] = child.get('TEXT', '')
                    id_to_parent_text[c_id] = p_text
                    id_to_node[c_id] = child
                    
        return root, id_to_text, id_to_parent_text, id_to_node, None
    except Exception as e:
        return None, None, None, None, f"파일 분석 오류: {str(e)}"

# -------------------------------------------------------------------------
# [관점 1] 씨수말 전수조사: 아들/딸 전수 나열 + 연결선(arrowlink) 기반 모마 및 외조부마(BMS) 추적
# -------------------------------------------------------------------------
def analyze_sire_perspective(root, target_sire_query, id_to_text, id_to_parent_text):
    query_norm = normalize_name(target_sire_query)
    results = []

    forward_arrows = defaultdict(list)
    backward_arrows = defaultdict(list)
    
    for node in root.iter('node'):
        src_id = node.get('ID')
        if not src_id:
            continue
        for arrow in node.findall('arrowlink'):
            dest_id = arrow.get('DESTINATION')
            if dest_id:
                forward_arrows[src_id].append(dest_id)
                backward_arrows[dest_id].append(src_id)

    def traverse(node):
        my_text = node.get('TEXT', '')
        if query_norm in normalize_name(my_text):
            for child in node.findall('node'):
                child_text = child.get('TEXT', '')
                child_id = child.get('ID')
                if not child_text:
                    continue

                dam_name = "미상"
                bms_name = "미상"

                target_dam_id = None
                if child_id in forward_arrows:
                    target_dam_id = forward_arrows[child_id][0]
                elif child_id in backward_arrows:
                    target_dam_id = backward_arrows[child_id][0]

                if target_dam_id and target_dam_id in id_to_text:
                    potential_dam = id_to_text[target_dam_id]
                    if query_norm not in normalize_name(potential_dam):
                        dam_name = potential_dam
                        potential_bms = id_to_parent_text.get(target_dam_id, "미상")
                        if potential_bms and potential_bms != "Unknown" and query_norm not in normalize_name(potential_bms):
                            bms_name = potential_bms

                results.append({
                    'progeny': child_text.strip(),
                    'dam': dam_name.strip(),
                    'bms': bms_name.strip()
                })

        for child in node.findall('node'):
            traverse(child)

    traverse(root)
    return results

# -------------------------------------------------------------------------
# [관점 2] 외조부마 관점: 직계 딸("암)" 표기)들의 자마 & 교배 부마 닉 분석
# -------------------------------------------------------------------------
def analyze_bms_perspective(root, target_sire_query, id_to_text, id_to_parent_text):
    query_norm = normalize_name(target_sire_query)
    results = []

    def traverse(node):
        my_text = node.get('TEXT', '')
        if query_norm in normalize_name(my_text):
            for child in node.findall('node'):
                child_text = child.get('TEXT', '')
                if '암)' in child_text:
                    progeny_list = []
                    seen_ids = set()
                    seen_combos = set()
                    
                    for arrow in child.findall('arrowlink'):
                        dest_id = arrow.get('DESTINATION')
                        if dest_id in id_to_text and dest_id not in seen_ids:
                            c_text = id_to_text[dest_id]
                            f_text = id_to_parent_text.get(dest_id, "정보 없음")
                            
                            combo_key = (c_text.strip(), f_text.strip())
                            if combo_key not in seen_combos:
                                progeny_list.append({'child': c_text, 'father': f_text})
                                seen_combos.add(combo_key)
                                
                            seen_ids.add(dest_id)
                            
                    if progeny_list:
                        results.append({
                            'daughter': child_text.strip(),
                            'progeny': progeny_list
                        })
        for child in node.findall('node'):
            traverse(child)

    traverse(root)
    return results

# UI 화면 타이틀
st.title("🐎 씨수말 & 외조부마(BMS) 통합 혈통 닉 분석기")

root_node, id_to_text, id_to_parent_text, id_to_node, err = load_mindmap_data()
if err:
    st.error(err)
    st.stop()

# 사이드바 설정 영역
st.sidebar.header("🔍 검색 설정")
search_sire = st.sidebar.text_input("씨수말 이름을 입력하세요", value="bernardini")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔀 분석 관점 선택")
view_mode = st.sidebar.radio("보고 싶은 분석을 선택하세요:", [
    "1. 씨수말(Sire) 관점 전수조사 (아들/딸 + 모마/외조부마)", 
    "2. 외조부마(BMS) 관점 분석 (직계딸의 자마 & 교배부마 닉)"
])

hide_unknown = False
if "1." in view_mode:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ 필터 옵션")
    hide_unknown = st.sidebar.checkbox("미상 항목 숨기기 (연결선 단절 데이터 삭제)", value=False)

st.sidebar.markdown("---")
highlight_special_progeny = st.sidebar.checkbox("🎯 특수 자마 하이라이트 (암말 @,#,* & 수말 G1-7+ 파란색 강조)", value=True)

if not search_sire.strip():
    st.info("👈 좌측 사이드바에 검색하고 싶은 씨수말 이름을 입력해 주세요.")
    st.stop()

sire_clean_name = clean_name_symbols(search_sire)
g1_pattern = re.compile(r'G1-(\d+)')

# =========================================================================
# [탭 1] 씨수말(Sire) 관점 전수조사 실행 결과 출력
# =========================================================================
if "1." in view_mode:
    st.subheader(f"1️⃣ 씨수말 [{sire_clean_name}] 관점 전수조사")
    st.caption("※ 씨수말이 배출한 아들·딸을 전수 나열하고, 연결선(arrowlink)이 있는 경우 모마와 외조부마(BMS)를 추적합니다. 선이 없는 경우 '미상'으로 표기됩니다.")
    
    sire_data = analyze_sire_perspective(root_node, search_sire, id_to_text, id_to_parent_text)
    
    if not sire_data:
        st.warning("조건에 맞는 자마 데이터가 없습니다.")
    else:
        filtered_data = []
        for item in sire_data:
            if hide_unknown and (item['dam'] == "미상" or item['bms'] == "미상"):
                continue
            filtered_data.append(item)

        bms_counts = defaultdict(int)
        for item in sire_data:
            if item['bms'] and item['bms'] != "미상":
                bms_counts[item['bms']] += 1
                
        nick_bms = [bms for bms, cnt in bms_counts.items() if cnt >= 2]
        single_bms = [bms for bms, cnt in bms_counts.items() if cnt == 1 and bms != "미상"]
        
        bg_palette = ["#FFEBEE", "#E0F2F1", "#F3E5F5", "#E8F5E9", "#FBE9E7", "#FFFDE7", "#E1F5FE"]
        border_palette = ["#D32F2F", "#00796B", "#7B1FA2", "#388E3C", "#E64A19", "#FBC02D", "#0288D1"]

        nick_style_map = {}
        for idx, ns in enumerate(nick_bms):
            nick_style_map[ns] = (border_palette[idx % len(border_palette)], bg_palette[idx % len(bg_palette)])

        st.markdown(f"""
        <div class='info-box'>
            <b>전체 배출 자마 수:</b> {len(sire_data)}두 | 
            <b>현재 표시 자마 수:</b> {len(filtered_data)}두 | 
            <b>중복 매칭된 외조부마(Nick BMS, 2두 이상):</b> <span style='color:#D32F2F; font-weight:bold;'>{len(nick_bms)}두</span> | 
            <b>단독 출현 외조부마(1두):</b> <span style='color:#0077CC; font-weight:bold;'>{len(single_bms)}두</span>
        </div>
        """, unsafe_allow_html=True)
        
        if nick_bms:
            st.markdown("**🎨 주요 외조부마(Nick BMS, 2두 이상) 범례:**")
            bms_html = "<div style='display:flex; flex-wrap:wrap; gap:8px; margin-bottom:15px;'>"
            for b in nick_bms:
                b_c, bg_c = nick_style_map[b]
                cnt = bms_counts[b]
                bms_html += f"<span style='background-color:{bg_c}; color:{b_c}; border:1px solid {b_c}; padding:4px 10px; border-radius:6px; font-weight:bold; font-size:0.9em;'>{clean_name_symbols(b)} ({cnt}두)</span>"
            bms_html += "</div>"
            st.markdown(bms_html, unsafe_allow_html=True)
            
        # 1. 주요 외조부마 범례별 파란색(특수) 자마 상세 목록 (상단 배치)
        st.markdown("---")
        st.markdown("### 🔍 주요 외조부마 범례별 파란색(특수) 자마 상세 목록")
        
        bms_grouped_items = defaultdict(list)
        for item in filtered_data:
            bms_full = item['bms']
            if bms_full and bms_full != "미상":
                bms_grouped_items[bms_full].append(item)

        for bms_name in nick_bms:
            items = bms_grouped_items[bms_name]
            blue_progenies = []
            for item in items:
                child_name = item['progeny']
                g1_match = g1_pattern.search(child_name)
                is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
                is_daughter = '암)' in child_name
                is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name or '*' in child_name) and is_daughter
                is_high_g1_son = is_high_g1 and not is_daughter
                
                if is_elite_daughter or is_high_g1_son:
                    blue_progenies.append(item)

            if blue_progenies:
                st.markdown(f"**🔹 {bms_name}** ({len(blue_progenies)}두 추출)")
                for item in blue_progenies:
                    dam_display = clean_name_symbols(item['dam']) if item['dam'] and item['dam'] != "미상" else "미상"
                    child_name = item['progeny']
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;- <span class='highlight-elite-daughter'>{child_name}</span> --- 🔗 (모마: {dam_display})", unsafe_allow_html=True)

        # 2. 단독 출현 외조부마(1두) 중 파란색 자마 목록 (범례별 상세 목록 바로 아래 배치)
        if single_bms:
            st.markdown("---")
            st.markdown("### 📌 단독 출현 외조부마 (1두) 중 파란색 자마 목록")
            for bms_name in single_bms:
                items = bms_grouped_items[bms_name]
                blue_progenies_single = []
                for item in items:
                    child_name = item['progeny']
                    g1_match = g1_pattern.search(child_name)
                    is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
                    is_daughter = '암)' in child_name
                    is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃
