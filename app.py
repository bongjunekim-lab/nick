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

def is_valid_mare(name, sire_query=""):
    """모마 명칭에 유효한 암말 조건이 포함되어 있는지 검증하고 자기 참조를 방어합니다."""
    if not name or name == "미상" or name == "Unknown":
        return False
    if '수)' in name and '암' not in name:
        return False
    if sire_query and normalize_name(sire_query) in normalize_name(name):
        return False  # 자기 참조(Self-reference) 데이터 오류 원천 차단
    return True

# 1. 페이지 설정
st.set_page_config(page_title="씨수말 & 외조부마(BMS) 통합 혈통 닉 분석기", layout="wide")

# CSS 스타일 정의
st.markdown("""
    <style>
    .elite-mare {
        color: #0055CC !important;
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
        color: #0055CC !important;
        font-weight: bold;
    }
    .highlight-elite-daughter {
        color: #0000FF !important;
        font-weight: 900 !important;
    }
    .highlight-g1-son {
        color: #0000FF !important;
        font-weight: 900 !important;
    }
    .star-daughter {
        color: #000000 !important;
        font-weight: 900 !important;
    }
    .legend-badge {
        font-size: 1.15em !important;
        font-weight: bold !important;
        padding: 6px 12px !important;
        border-radius: 6px;
        display: inline-block;
    }
    .single-sire-title {
        font-size: 1.15em !important;
        font-weight: bold !important;
        padding: 6px 12px !important;
        border-radius: 6px;
        display: inline-block;
        background-color: #E3F2FD !important;
        color: #0055CC !important;
        border: 1px solid #0055CC !important;
        margin-top: 10px;
        margin-bottom: 5px;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_mindmap_data():
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
# [관점 1] 씨수말 전수조사 분석 함수 (구조적 역전 및 자기 참조 방어 보완)
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
                    
                    # 자기 참조 혹은 수말 오인식 방어
                    if not is_valid_mare(potential_dam, target_sire_query) and query_norm not in normalize_name(potential_dam):
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
# [관점 2] 외조부마(BMS) 관점 분석 함수
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
                    
                    daughter_norm = normalize_name(child_text)

                    for arrow in child.findall('arrowlink'):
                        dest_id = arrow.get('DESTINATION')
                        if dest_id in id_to_text and dest_id not in seen_ids:
                            c_text = id_to_text[dest_id]
                            f_text = id_to_parent_text.get(dest_id, "정보 없음")
                            
                            if normalize_name(c_text) == daughter_norm:
                                seen_ids.add(dest_id)
                                continue

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

st.title("🐎 씨수말 & 외조부마(BMS) 통합 혈통 닉 분석기")

root_node, id_to_text, id_to_parent_text, id_to_node, err = load_mindmap_data()
if err:
    st.error(err)
    st.stop()

st.sidebar.header("🔍 검색 설정")
search_sire = st.sidebar.text_input("씨수말 이름을 입력하세요", value="storm cat")

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
    st.caption("※ 씨수말이 배출한 아들·딸을 전수 나열하고, 연결선(arrowlink)이 있는 경우 모마와 외조부마(BMS)를 추적합니다.")
    
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
        
        bg_palette = ["#E3F2FD", "#E0F2F1", "#F3E5F5", "#E8F5E9", "#FBE9E7", "#FFFDE7", "#E1F5FE"]
        border_palette = ["#0055CC", "#00796B", "#7B1FA2", "#388E3C", "#E64A19", "#FBC02D", "#0288D1"]

        nick_style_map = {}
        for idx, ns in enumerate(nick_bms):
            nick_style_map[ns] = (border_palette[idx % len(border_palette)], bg_palette[idx % len(bg_palette)])

        st.markdown(f"""
        <div class='info-box'>
            <b>전체 배출 자마 수:</b> {len(sire_data)}두 | 
            <b>현재 표시 자마 수:</b> {len(filtered_data)}두 | 
            <b>중복 매칭된 외조부마(Nick BMS, 2두 이상):</b> <span style='color:#0055CC; font-weight:bold;'>{len(nick_bms)}두</span> | 
            <b>단독 출현 외조부마(1두):</b> <span style='color:#0077CC; font-weight:bold;'>{len(single_bms)}두</span>
        </div>
        """, unsafe_allow_html=True)
        
        bms_grouped_items = defaultdict(list)
        for item in filtered_data:
            bms_full = item['bms']
            if bms_full and bms_full != "미상":
                bms_grouped_items[bms_full].append(item)

        if nick_bms:
            st.markdown("**🎨 주요 외조부마(Nick BMS, 2두 이상) 범례 및 파란색(특수) 자마 목록:**")
            for bms_name in nick_bms:
                b_c, bg_c = nick_style_map[bms_name]
                cnt = bms_counts[bms_name]
                
                badge_html = f"<div style='margin-top: 10px;'><span class='legend-badge' style='background-color:{bg_c}; color:{b_c}; border:1px solid {b_c};'>{clean_name_symbols(bms_name)} ({cnt}두)</span></div>"
                st.markdown(badge_html, unsafe_allow_html=True)
                
                items = bms_grouped_items[bms_name]
                blue_progenies = []
                for item in items:
                    if not is_valid_mare(item['dam'], search_sire):
                        continue
                        
                    child_name = item['progeny']
                    g1_match = g1_pattern.search(child_name)
                    is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
                    has_am_tag = '암)' in child_name
                    is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name or '*' in child_name) and has_am_tag
                    is_high_g1_son = is_high_g1 and not has_am_tag
                    
                    if is_elite_daughter or is_high_g1_son:
                        blue_progenies.append(item)
                
                if blue_progenies:
                    for item in blue_progenies:
                        dam_display = clean_name_symbols(item['dam'])
                        child_name = item['progeny']
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ <span class='highlight-elite-daughter'>{child_name}</span> --- 🔗 (모마: {dam_display})", unsafe_allow_html=True)
                else:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ <span style='color: #888; font-style: italic;'>조건을 만족하는 파란색 자마 없음</span>", unsafe_allow_html=True)

        if single_bms:
            st.markdown("---")
            st.markdown("### 📌 단독 출현 외조부마 (1두) 목록")
            for bms_name in single_bms:
                items = bms_grouped_items[bms_name]
                blue_progenies_single = []
                for item in items:
                    if not is_valid_mare(item['dam'], search_sire):
                        continue
                        
                    child_name = item['progeny']
                    g1_match = g1_pattern.search(child_name)
                    is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
                    has_am_tag = '암)' in child_name
                    is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name or '*' in child_name) and has_am_tag
                    is_high_g1_son = is_high_g1 and not has_am_tag
                    
                    if is_elite_daughter or is_high_g1_son:
                        blue_progenies_single.append(item)
                
                if blue_progenies_single:
                    st.markdown(f"<div style='margin-top: 10px;'><span class='single-sire-title'>{bms_name} (1두)</span></div>", unsafe_allow_html=True)
                    for item in blue_progenies_single:
                        dam_display = clean_name_symbols(item['dam'])
                        child_name = item['progeny']
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ <span class='highlight-elite-daughter'>{child_name}</span> --- 🔗 (모마: {dam_display})", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 전체 자마 리스트 및 외조부마 매칭")
        for idx, item in enumerate(filtered_data, 1):
            bms_display = clean_name_symbols(item['bms']) if item['bms'] and item['bms'] != "미상" else "미상"
            dam_display = clean_name_symbols(item['dam']) if item['dam'] and item['dam'] != "미상" else "미상"
            
            child_name = item['progeny']
            g1_match = g1_pattern.search(child_name)
            is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
            has_am_tag = '암)' in child_name
            is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name or '*' in child_name) and has_am_tag
            is_high_g1_son = is_high_g1 and not has_am_tag

            if highlight_special_progeny:
                if is_high_g1_son:
                    child_display = f"<span class='highlight-g1-son'>{child_name}</span>"
                elif is_elite_daughter:
                    child_display = f"<span class='highlight-elite-daughter'>{child_name}</span>"
                else:
                    child_display = child_name
            else:
                if is_high_g1_son or is_elite_daughter:
                    child_display = f"<span class='premium-progeny'>{child_name}</span>"
                else:
                    child_display = child_name

            dam_str = f"--- 🔗 (모마: {dam_display})"
            
            if item['bms'] in nick_style_map:
                b_c, bg_c = nick_style_map[item['bms']]
                bms_style = f"| <span style='color:{b_c}; background-color:{bg_c}; font-weight:bold; padding:2px 6px; border-radius:4px; border:1px solid {b_c}80;'>[외조부마: {bms_display}]</span>"
            else:
                bms_style = f"| [외조부마: {bms_display}]"
                
            st.markdown(f"<div class='progeny-item'>🐴 [{idx}] <b>{child_display}</b> {dam_str} {bms_style}</div>", unsafe_allow_html=True)

# =========================================================================
# [탭 2] 외조부마(BMS) 관점 분석 실행 결과 출력
# =========================================================================
else:
    st.subheader(f"2️⃣ 외조부마(BMS) [{sire_clean_name}] 관점 분석")
    st.caption(f"※ 해당 씨수말의 직계 딸('암)' 표기)들이 배출한 자마 및 교배 부마(Father)의 닉(Nick) 조합을 분석합니다.")
    
    bms_data = analyze_bms_perspective(root_node, search_sire, id_to_text, id_to_parent_text)
    
    if not bms_data:
        st.warning(f"'{search_sire}'의 조건('암)' 표기 + 연결된 자마 보유)을 만족하는 직계 딸 데이터가 없습니다.")
    else:
        father_counts = defaultdict(int)
        father_grouped_progenies = defaultdict(list)

        for item in bms_data:
            daughter_name = item['daughter']
            for p in item['progeny']:
                f_name = p['father']
                father_counts[f_name] += 1
                father_grouped_progenies[f_name].append({
                    'daughter': daughter_name,
                    'child': p['child']
                })

        nick_sires = [father for father, count in father_counts.items() if count >= 2 and father != "정보 없음"]
        single_sires = [father for father, count in father_counts.items() if count == 1 and father != "정보 없음"]

        bg_palette = ["#E3F2FD", "#E0F2F1", "#F3E5F5", "#E8F5E9", "#FBE9E7", "#FFFDE7", "#E1F5FE"]
        border_palette = ["#0055CC", "#00796B", "#7B1FA2", "#388E3C", "#E64A19", "#FBC02D", "#0288D1"]

        nick_style_map = {}
        for idx, ns in enumerate(nick_sires):
            nick_style_map[ns] = (border_palette[idx % len(border_palette)], bg_palette[idx % len(bg_palette)])

        st.markdown(f"""
        <div class='info-box'>
            <b>조건 충족 직계 딸(종빈마):</b> 총 {len(bms_data)}두 | 
            <b>중복 교배(Nick) 부마 수:</b> <span style='color:#0055CC; font-weight:bold;'>{len(nick_sires)}두</span> | 
            <b>단독 출현 씨수말 수:</b> <span style='color:#0077CC; font-weight:bold;'>{len(single_sires)}두</span>
        </div>
        """, unsafe_allow_html=True)

        if nick_sires:
            st.markdown("🎨 **중복 교배 부마(Nick) 하이라이트 범례 및 파란색(특수) 자마 목록:**")
            for ns in nick_sires:
                b_c, bg_c = nick_style_map[ns]
                cnt = father_counts[ns]
                
                badge_html = f"<div style='margin-top: 10px;'><span class='legend-badge' style='background-color:{bg_c}; color:{b_c}; border:1px solid {b_c};'>{ns} ({cnt}두)</span></div>"
                st.markdown(badge_html, unsafe_allow_html=True)
                
                progenies = father_grouped_progenies[ns]
                blue_progenies = []
                for p in progenies:
                    child_name = p['child']
                    g1_match = g1_pattern.search(child_name)
                    is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
                    has_am_tag = '암)' in child_name
                    is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name or '*' in child_name) and has_am_tag
                    is_high_g1_son = is_high_g1 and not has_am_tag
                    
                    if is_elite_daughter or is_high_g1_son:
                        blue_progenies.append(p)
                
                if blue_progenies:
                    for p in blue_progenies:
                        daughter_name = p['daughter']
                        child_name = p['child']
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ {sire_clean_name} 직계딸: {daughter_name} --- <span class='highlight-elite-daughter'>{child_name}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ <span style='color: #888; font-style: italic;'>조건을 만족하는 파란색 자마 없음</span>", unsafe_allow_html=True)

        if single_sires:
            st.markdown("---")
            st.markdown("### 📌 단독 출현 씨수말 목록")
            for ns in single_sires:
                progenies = father_grouped_progenies[ns]
                blue_progenies_single = []
                for p in progenies:
                    child_name = p['child']
                    g1_match = g1_pattern.search(child_name)
                    is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
                    has_am_tag = '암)' in child_name
                    is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name or '*' in child_name) and has_am_tag
                    is_high_g1_son = is_high_g1 and not has_am_tag
                    
                    if is_elite_daughter or is_high_g1_son:
                        blue_progenies_single.append(p)
                
                if blue_progenies_single:
                    st.markdown(f"<div style='margin-top: 10px;'><span class='single-sire-title'>{ns} (1두)</span></div>", unsafe_allow_html=True)
                    for p in blue_progenies_single:
                        daughter_name = p['daughter']
                        child_name = p['child']
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ {sire_clean_name} 직계딸: {daughter_name} --- <span class='highlight-elite-daughter'>{child_name}</span>", unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("### 📋 직계 딸별 자마 및 교배 부마 매칭")
        for idx, item in enumerate(bms_data, 1):
            daughter_name = item['daughter']
            progeny_list = item['progeny']
            
            st.markdown(f"<div class='elite-mare'>💎 [{idx}] {sire_clean_name} 직계딸: {daughter_name} (연결 자마: {len(progeny_list)}두)</div>", unsafe_allow_html=True)
            
            for p in progeny_list:
                child_name = p['child']
                father_name = p['father']
                
                g1_match = g1_pattern.search(child_name)
                is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
                has_am_tag = '암)' in child_name
                is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name or '*' in child_name) and has_am_tag
                is_high_g1_son = is_high_g1 and not has_am_tag
                
                if highlight_special_progeny:
                    if is_high_g1_son:
                        child_display = f"<span class='highlight-g1-son'>{child_name}</span>"
                    elif is_elite_daughter:
                        child_display = f"<span class='highlight-elite-daughter'>{child_name}</span>"
                    else:
                        child_display = child_name
                else:
                    if is_high_g1_son or is_elite_daughter:
                        child_display = f"<span class='premium-progeny'>{child_name}</span>"
                    else:
                        child_display = child_name

                if father_name in nick_style_map:
                    b_c, bg_c = nick_style_map[father_name]
                    father_display = f"<span style='color:{b_c}; background-color:{bg_c}; font-weight:bold; padding:2px 8px; border-radius:4px; border:1px solid {b_c}80;'>{father_name}</span>"
                else:
                    father_display = f"<b>{father_name}</b>"
                    
                st.markdown(f"<div class='progeny-item'>🔗 [연결 자마] {child_display} (부마: {father_display})</div>", unsafe_allow_html=True)
