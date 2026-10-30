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
    clean = text.replace('@', '').replace('#', '').replace('*', '').replace('$', '')
    clean = clean.replace('＠', '').replace('＃', '')
    clean = clean.replace('암)', '').replace('수)', '').replace('거)', '')
    clean = clean.replace('가.', '').replace('나.', '').replace('다.', '')
    clean = clean.split('(')[0]
    return clean.strip().lower()

def is_valid_mare(name):
    """
    [안전하고 유연한 암말 검증 원칙]
    - 마명 내에 '암' 글자가 포함되어 있으면 암말(직계딸)로 인정합니다.
    - 단, 명백한 수말(수) 표기가 단독으로 강조된 경우는 제외합니다.
    """
    if not name:
        return False
    if '수)' in name and '암' not in name:
        return False
    if '암' in name or '암)' in name:
        return True
    if 'speightstown' in name.lower() or 'sire' in name.lower():
        return False
    return True

# 1. 페이지 설정
st.set_page_config(page_title="씨수말 & 외조부마(BMS) 통합 혈통 닉 분석기", layout="wide")

# CSS 스타일 정의
st.markdown("""
    <style>
    .elite-mare {
        color: #1B4F72 !important;
        font-weight: bold;
        font-size: 1.25em;
        margin-top: 35px;
        margin-bottom: 8px;
        padding-top: 15px;
        border-top: 1px dashed #D5D8DC;
    }
    .progeny-item {
        margin-left: 25px;
        margin-bottom: 5px;
        color: #2C3E50;
        font-size: 1.05em;
    }
    .highlight-elite-daughter {
        color: #1B4F72 !important;
        font-weight: 900 !important;
    }
    .highlight-dash-mare {
        font-weight: bold !important;
        color: #000000 !important;
    }
    .highlight-g1-son {
        color: #1B4F72 !important;
        font-weight: 900 !important;
    }
    .legend-badge {
        font-size: 1.15em !important;
        font-weight: bold !important;
        padding: 6px 12px !important;
        border-radius: 6px;
        display: inline-block;
    }
    .info-box {
        background-color: #F8F9F9;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
        border: 1px solid #D5DBDB;
    }
    .tier-badge-legendary {
        background: linear-gradient(135deg, #F39C12, #D35400);
        color: #fff;
        padding: 2px 8px;
        border-radius: 10px;
        font-weight: bold;
        font-size: 0.85em;
        border: 1px solid #BA4A00;
    }
    .tier-badge-s-plus {
        background: linear-gradient(135deg, #5499C7, #1B4F72);
        color: #fff;
        padding: 2px 8px;
        border-radius: 10px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .tier-badge-s {
        background: linear-gradient(135deg, #7FB3D5, #5499C7);
        color: #fff;
        padding: 2px 8px;
        border-radius: 10px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .tier-badge-a {
        background: linear-gradient(135deg, #95A5A6, #7F8C8D);
        color: #fff;
        padding: 2px 8px;
        border-radius: 10px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .gauge-container {
        background-color: #F2F4F4;
        border-radius: 4px;
        width: 100%;
        height: 6px;
        margin-top: 3px;
        margin-bottom: 10px;
        overflow: hidden;
        border: 1px solid #EAEDED;
    }
    .gauge-bar {
        height: 100%;
        background: linear-gradient(90deg, #D4E6F1, #85C1E9);
        border-radius: 3px;
    }
    .summary-card-top {
        background: linear-gradient(135deg, #F2F4F4, #E5E7E9);
        border: 2px solid #1B4F72;
        padding: 15px 20px;
        border-radius: 8px;
        text-align: center;
        margin-top: 15px;
        margin-bottom: 20px;
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

def calculate_evaluation_score(text, is_elite_daughter=False, is_high_g1=False):
    score = 30.0
    g1_match = re.search(r'G1-(\d+)', text)
    g1_wins = int(g1_match.group(1)) if g1_match else 0
    
    score += g1_wins * 10.0
    if is_elite_daughter:
        score += 30.0
    if is_high_g1:
        score += 20.0
    if '전' in text and '승' in text:
        score += 15.0
        
    if score >= 300.0:
        badge_html = "<span class='tier-badge-legendary'>🌟 LEGENDARY S++</span>"
    elif score >= 150.0:
        badge_html = "<span class='tier-badge-s-plus'>👑 S+ Tier</span>"
    elif score >= 80.0:
        badge_html = "<span class='tier-badge-s'>🔥 S Tier</span>"
    else:
        badge_html = "<span class='tier-badge-a'>✨ A Tier</span>"
        
    return score, badge_html

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
                    if query_norm not in normalize_name(potential_dam) and is_valid_mare(potential_dam):
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

def analyze_bms_perspective(root, target_sire_query, id_to_text, id_to_parent_text):
    query_norm = normalize_name(target_sire_query)
    results = []

    def traverse(node):
        my_text = node.get('TEXT', '')
        if query_norm in normalize_name(my_text):
            for child in node.findall('node'):
                child_text = child.get('TEXT', '')
                if is_valid_mare(child_text):
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

# UI 화면 타이틀
st.title("🐎 씨수말 & 외조부마(BMS) 통합 혈통 닉 분석기")

root_node, id_to_text, id_to_parent_text, id_to_node, err = load_mindmap_data()
if err:
    st.error(err)
    st.stop()

# 사이드바 설정 영역
st.sidebar.header("🔍 검색 설정")
search_sire = st.sidebar.text_input("씨수말 이름을 입력하세요", value="Never Bend")

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
highlight_special_progeny = st.sidebar.checkbox("🎯 특수 자마 하이라이트 (암말 @,#,* & 수말 G1-7+ 진한 파란색 강조)", value=True)

if not search_sire.strip():
    st.info("👈 좌측 사이드바에 검색하고 싶은 씨수말 이름을 입력해 주세요.")
    st.stop()

sire_clean_name = clean_name_symbols(search_sire)
g1_pattern = re.compile(r'G1-(\d+)')

# 사전 점수 집계 (상단 스코어보드 공용)
sire_data_for_calc = analyze_sire_perspective(root_node, search_sire, id_to_text, id_to_parent_text)
total_sire_score = sum(calculate_evaluation_score(item['progeny'])[0] for item in sire_data_for_calc)

bms_data_for_calc = analyze_bms_perspective(root_node, search_sire, id_to_text, id_to_parent_text)
total_bms_score = 0.0
for item in bms_data_for_calc:
    for p in item['progeny']:
        c_name = p['child']
        is_ed = is_valid_mare(c_name) and any(sym in c_name for sym in ['@', '#', '*'])
        g_match = g1_pattern.search(c_name)
        g1_wins = int(g_match.group(1)) if g_match else 0
        is_hg1 = (not is_valid_mare(c_name)) and (g1_wins >= 7)
        s, _ = calculate_evaluation_score(c_name, is_elite_daughter=is_ed, is_high_g1=is_hg1)
        total_bms_score += s

total_comprehensive_score = total_sire_score + total_bms_score

# 🚀 [상단 배치] 최종 종합 브리딩 스코어보드 카드
st.markdown(f"""
<div class='summary-card-top'>
    <h3 style='margin: 0; color: #2E4053;'>🏆 [{sire_clean_name}] 최종 종합 브리딩 스코어보드</h3>
    <p style='font-size: 0.95em; margin: 5px 0 10px 0; color: #566573;'>씨수말 직계 기여도와 씨암말(외조부마) 모계 파급력을 전략적으로 합산한 최종 평가입니다.</p>
    <hr style='border: 0.5px solid #1B4F72; width: 40%; margin: 8px auto;'>
    <h4 style='margin: 5px 0; color: #2C3E50;'>✨ 종합 통합 점수: <span style='color: #1B4F72;'>{total_comprehensive_score:.1f} 점</span></h4>
    <p style='font-size: 0.9em; margin: 0; color: #5D6D7E;'>씨수말 누적 점수: <b>{total_sire_score:.1f}점</b> | 씨암말(외조부마) 누적 점수: <b>{total_bms_score:.1f}점</b></p>
</div>
""", unsafe_allow_html=True)

# =========================================================================
# [탭 1] 씨수말(Sire) 관점 전수조사 실행 결과 출력
# =========================================================================
if "1." in view_mode:
    st.subheader(f"1️⃣ 씨수말 [{sire_clean_name}] 관점 전수조사 (Layer A: 직계 자마 & 외조부마 매칭)")
    st.caption("※ 씨수말이 직접 배출한 직계 자마와 결합된 외조부마(BMS) 간의 닉 효율 및 Sire-Maker 결합 패턴을 분석합니다.")
    
    sire_data = sire_data_for_calc
    
    if not sire_data:
        st.warning("조건에 맞는 자마 데이터가 없습니다.")
    else:
        filtered_data = []
        for item in sire_data:
            if hide_unknown and (item['dam'] == "미상" or item['bms'] == "미상"):
                continue
            filtered_data.append(item)

        bms_counts = defaultdict(int)
        bms_has_special_progeny = defaultdict(bool)
        
        for item in sire_data:
            bms = item['bms']
            if bms and bms != "미상":
                bms_counts[bms] += 1
                c_name = item['progeny']
                g_match = g1_pattern.search(c_name)
                g_wins = int(g_match.group(1)) if g_match else 0
                is_dau = is_valid_mare(c_name)
                # ✅ [조건 반영] 1. 암말 @, #, * 기호 보유 OR 2. 수말 G1-7두 이상 배출
                if (is_dau and any(sym in c_name for sym in ['@', '#', '*'])) or (not is_dau and g_wins >= 7):
                    bms_has_special_progeny[bms] = True

        # ✅ 닉(2두 이상)이 아니더라도, 특수 자마를 1두라도 보유했다면 무조건 타겟에 포함!
        target_bms_list = [bms for bms in bms_counts.keys() if bms != "미상" and (bms_counts[bms] >= 2 or bms_has_special_progeny[bms])]
        
        total_progeny_count = len(sire_data)
        
        elite_count = 0
        for item in sire_data:
            c_name = item['progeny']
            g_match = g1_pattern.search(c_name)
            g_wins = int(g_match.group(1)) if g_match else 0
            is_dau = is_valid_mare(c_name)
            if (is_dau and any(sym in c_name for sym in ['@', '#', '*'])) or (not is_dau and g_wins >= 7):
                elite_count += 1

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="📊 직계 배출 자마 수", value=f"{total_progeny_count}두")
        with col2:
            st.metric(label="🌟 엘리트/G급 자마", value=f"{elite_count}두")
        with col3:
            st.metric(label="🧬 씨수말 누적 스코어", value=f"{total_sire_score:.1f}점")
        with col4:
            st.metric(label="🏛️ 씨암말(외조부마) 누적 스코어", value=f"{total_bms_score:.1f}점")

        bg_palette = ["#EBF5FB", "#E8F8F5", "#F4ECF7", "#EAFAF1", "#FDEBD0", "#FEF9E7", "#EAF2F8"]
        border_palette = ["#1B4F72", "#16A085", "#8E44AD", "#27AE60", "#D35400", "#F39C12", "#2980B9"]

        nick_style_map = {}
        for idx, ns in enumerate(target_bms_list):
            nick_style_map[ns] = (border_palette[idx % len(border_palette)], bg_palette[idx % len(bg_palette)])

        st.markdown(f"""
        <div class='info-box'>
            <b>전체 배출 자마 수:</b> {len(sire_data)}두 | 
            <b>현재 표시 자마 수:</b> {len(filtered_data)}두 | 
            <b>주요 외조부마(2두 이상 또는 특수자마 보유):</b> <span style='color:#1B4F72; font-weight:bold;'>{len(target_bms_list)}두</span>
        </div>
        """, unsafe_allow_html=True)
        
        bms_grouped_items = defaultdict(list)
        for item in filtered_data:
            bms_full = item['bms']
            if bms_full and bms_full != "미상":
                bms_grouped_items[bms_full].append(item)

        if target_bms_list:
            st.markdown("🎨 **주요 외조부마 범례 및 특수 자마 목록 (암말 @,#,* / 수말 G1-7두+):**")
            for bms_name in target_bms_list:
                b_c, bg_c = nick_style_map[bms_name]
                cnt = bms_counts[bms_name]
                badge_html = f"<div style='margin-top: 10px;'><span class='legend-badge' style='background-color:{bg_c}; color:{b_c}; border:1px solid {b_c};'>{clean_name_symbols(bms_name)} ({cnt}두)</span></div>"
                st.markdown(badge_html, unsafe_allow_html=True)
                
                items = bms_grouped_items[bms_name]
                special_progenies = []
                for item in items:
                    child_name = item['progeny']
                    g1_match = g1_pattern.search(child_name)
                    g1_wins = int(g1_match.group(1)) if g1_match else 0
                    is_daughter = is_valid_mare(child_name)
                    
                    is_high_g1_son = (not is_daughter) and (g1_wins >= 7)
                    is_elite_daughter = is_daughter and any(sym in child_name for sym in ['@', '#', '*'])
                    
                    if is_elite_daughter or is_high_g1_son:
                        special_progenies.append(item)
                
                if special_progenies:
                    for item in special_progenies:
                        dam_display = clean_name_symbols(item['dam']) if item['dam'] and item['dam'] != "미상" else "미상"
                        child_name = item['progeny']
                        is_daughter = is_valid_mare(child_name)
                        g1_match = g1_pattern.search(child_name)
                        g1_wins = int(g1_match.group(1)) if g1_match else 0
                        
                        is_high_g1_son = (not is_daughter) and (g1_wins >= 7)
                        is_elite_daughter = is_daughter and any(sym in child_name for sym in ['@', '#', '*'])
                        
                        score, badge_h = calculate_evaluation_score(child_name, is_elite_daughter=is_elite_daughter, is_high_g1=is_high_g1_son)
                        
                        if is_elite_daughter:
                            c_display = f"<span class='highlight-elite-daughter'>{child_name}</span>"
                        elif is_high_g1_son:
                            c_display = f"<span class='highlight-g1-son'>{child_name}</span>"
                        else:
                            c_display = child_name
                            
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ {badge_h} {c_display} --- 🔗 (모마: {dam_display}) [가중 점수: <b>{score:.1f}점</b>]", unsafe_allow_html=True)
                else:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ <span style='color: #888; font-style: italic;'>조건(암말 @,#,* 또는 수말 G1-7두+)을 만족하는 자마 없음</span>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 전체 자마 리스트 및 외조부마 매칭 (Layer A 원본 데이터)")
        for idx, item in enumerate(filtered_data, 1):
            bms_display = clean_name_symbols(item['bms']) if item['bms'] and item['bms'] != "미상" else "미상"
            dam_display = clean_name_symbols(item['dam']) if item['dam'] and item['dam'] != "미상" else "미상"
            child_name = item['progeny']
            g1_match = g1_pattern.search(child_name)
            g1_wins = int(g1_match.group(1)) if g1_match else 0
            is_daughter = is_valid_mare(child_name)
            
            is_high_g1_son = (not is_daughter) and (g1_wins >= 7)
            is_elite_daughter = is_daughter and any(sym in child_name for sym in ['@', '#', '*'])

            if highlight_special_progeny:
                if is_high_g1_son:
                    child_display = f"<span class='highlight-g1-son'>{child_name}</span>"
                elif is_elite_daughter:
                    child_display = f"<span class='highlight-elite-daughter'>{child_name}</span>"
                elif '-' in child_name and is_daughter:
                    child_display = f"<span class='highlight-dash-mare'>{child_name}</span>"
                else:
                    child_display = child_name
            else:
                child_display = child_name

            dam_str = f"--- 🔗 (모마: {dam_display})"
            
            if item['bms'] in nick_style_map:
                b_c, bg_c = nick_style_map[item['bms']]
                bms_style = f"| <span style='color:{b_c}; background-color:{bg_c}; font-weight:bold; padding:2px 6px; border-radius:4px; border:1px solid {b_c}80;>[외조부마: {bms_display}]</span>"
            else:
                bms_style = f"| [외조부마: {bms_display}]"
                
            score, badge_h = calculate_evaluation_score(child_name, is_elite_daughter=is_elite_daughter, is_high_g1=is_high_g1_son)
            st.markdown(f"<div class='progeny-item'>🐴 [{idx}] {badge_h} <b>{child_display}</b> {dam_str} {bms_style} (가중 점수: <b>{score:.1f}점</b>)</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='margin-left: 25px;'><div class='gauge-container'><div class='gauge-bar' style='width: {min(score/5, 100)}%;'></div></div></div>", unsafe_allow_html=True)

# =========================================================================
# [탭 2] 외조부마(BMS) 관점 분석 실행 결과 출력
# =========================================================================
else:
    st.subheader(f"2️⃣ 외조부마(BMS) [{sire_clean_name}] 관점 분석 (Layer B: 모계 확장 축)")
    st.caption(f"※ 해당 씨수말의 직계 딸('암)' 표기)들이 배출한 자마 및 교배 부마(Father)의 닉(Nick) 조합을 분석합니다.")
    
    bms_data = bms_data_for_calc
    
    if not bms_data:
        st.warning(f"'{search_sire}'의 조건('암)' 표기 + 연결된 자마 보유)을 만족하는 직계 딸 데이터가 없습니다.")
    else:
        father_counts = defaultdict(int)
        father_has_special_progeny = defaultdict(bool)
        father_grouped_progenies = defaultdict(list)

        for item in bms_data:
            daughter_name = item['daughter']
            for p in item['progeny']:
                f_name = p['father']
                father_counts[f_name] += 1
                
                c_name = p['child']
                g_match = g1_pattern.search(c_name)
                g_wins = int(g_match.group(1)) if g_match else 0
                is_dau = is_valid_mare(c_name)
                if (is_dau and any(sym in c_name for sym in ['@', '#', '*'])) or (not is_dau and g_wins >= 7):
                    father_has_special_progeny[f_name] = True

                father_grouped_progenies[f_name].append({
                    'daughter': daughter_name,
                    'child': c_name
                })

        target_sires = [father for father in father_counts.keys() if father != "정보 없음" and (father_counts[father] >= 2 or father_has_special_progeny[father])]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="💎 조건 충족 직계딸(종빈마)", value=f"{len(bms_data)}두")
        with col2:
            st.metric(label="🔗 연결된 총 후대 자마", value=f"{sum(len(item['progeny']) for item in bms_data)}두")
        with col3:
            st.metric(label="🏛️ 씨암말(외조부마) 누적 스코어", value=f"{total_bms_score:.1f}점")
        with col4:
            st.metric(label="🧬 씨수말 누적 스코어", value=f"{total_sire_score:.1f}점")

        bg_palette = ["#EBF5FB", "#E8F8F5", "#F4ECF7", "#EAFAF1", "#FDEBD0", "#FEF9E7", "#EAF2F8"]
        border_palette = ["#1B4F72", "#16A085", "#8E44AD", "#27AE60", "#D35400", "#F39C12", "#2980B9"]

        nick_style_map = {}
        for idx, ns in enumerate(target_sires):
            nick_style_map[ns] = (border_palette[idx % len(border_palette)], bg_palette[idx % len(bg_palette)])

        if target_sires:
            st.markdown("🎨 **주요 교배 부마 하이라이트 범례 및 특수 자마 목록 (암말 @,#,* / 수말 G1-7두+):**")
            for ns in target_sires:
                b_c, bg_c = nick_style_map[ns]
                cnt = father_counts[ns]
                badge_html = f"<div style='margin-top: 10px;'><span class='legend-badge' style='background-color:{bg_c}; color:{b_c}; border:1px solid {b_c};'>{ns} ({cnt}두)</span></div>"
                st.markdown(badge_html, unsafe_allow_html=True)
                
                progenies = father_grouped_progenies[ns]
                special_progenies = []
                for p in progenies:
                    child_name = p['child']
                    g1_match = g1_pattern.search(child_name)
                    g1_wins = int(g1_match.group(1)) if g1_match else 0
                    is_daughter = is_valid_mare(child_name)
                    
                    is_high_g1_son = (not is_daughter) and (g1_wins >= 7)
                    is_elite_daughter = is_daughter and any(sym in child_name for sym in ['@', '#', '*'])
                    
                    if is_elite_daughter or is_high_g1_son:
                        special_progenies.append(p)
                
                if special_progenies:
                    for p in special_progenies:
                        daughter_name = p['daughter']
                        child_name = p['child']
                        is_daughter = is_valid_mare(child_name)
                        g1_match = g1_pattern.search(child_name)
                        g1_wins = int(g1_match.group(1)) if g1_match else 0
                        
                        is_high_g1_son = (not is_daughter) and (g1_wins >= 7)
                        is_elite_daughter = is_daughter and any(sym in child_name for sym in ['@', '#', '*'])
                        
                        score, badge_h = calculate_evaluation_score(child_name, is_elite_daughter=is_elite_daughter, is_high_g1=is_high_g1_son)
                        
                        if is_elite_daughter:
                            c_display = f"<span class='highlight-elite-daughter'>{child_name}</span>"
                        elif is_high_g1_son:
                            c_display = f"<span class='highlight-g1-son'>{child_name}</span>"
                        else:
                            c_display = child_name
                            
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ {badge_h} 직계딸: {daughter_name} --- {c_display} (가중 점수: <b>{score:.1f}점</b>)", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 직계 딸별 자마 및 교배 부마 매칭")
        for idx, item in enumerate(bms_data, 1):
            daughter_name = item['daughter']
            progeny_list = item['progeny']
            
            mare_scores = []
            for p in progeny_list:
                c_name = p['child']
                is_ed = is_valid_mare(c_name) and any(sym in c_name for sym in ['@', '#', '*'])
                g_match = g1_pattern.search(c_name)
                g1_wins = int(g_match.group(1)) if g_match else 0
                is_hg1 = (not is_valid_mare(c_name)) and (g1_wins >= 7)
                s, _ = calculate_evaluation_score(c_name, is_elite_daughter=is_ed, is_high_g1=is_hg1)
                mare_scores.append(s)
            
            if mare_scores:
                max_score = max(mare_scores)
                avg_score = sum(mare_scores) / len(mare_scores)
                g1_density_bonus = sum(1 for s in mare_scores if s >= 100.0) * 20.0
                hybrid_mare_score = (max_score * 0.6) + (avg_score * 0.2) + g1_density_bonus
            else:
                hybrid_mare_score = 30.0

            if hybrid_mare_score >= 300.0:
                mare_badge = "<span class='tier-badge-legendary'>🌟 LEGENDARY S++</span>"
            elif hybrid_mare_score >= 150.0:
                mare_badge = "<span class='tier-badge-s-plus'>👑 S+ Tier</span>"
            elif hybrid_mare_score >= 80.0:
                mare_badge = "<span class='tier-badge-s'>🔥 S Tier</span>"
            else:
                mare_badge = "<span class='tier-badge-a'>✨ A Tier</span>"

            st.markdown(f"<div class='elite-mare'>💎 [{idx}] {mare_badge} {daughter_name} (연결 자마: {len(progeny_list)}두) — 모마 하이브리드 종합 평가: <b>{hybrid_mare_score:.1f}점</b></div>", unsafe_allow_html=True)
            
            for p in progeny_list:
                child_name = p['child']
                father_name = p['father']
                g1_match = g1_pattern.search(child_name)
                g1_wins = int(g1_match.group(1)) if g1_match else 0
                is_daughter = is_valid_mare(child_name)
                
                is_high_g1_son = (not is_daughter) and (g1_wins >= 7)
                is_elite_daughter = is_daughter and any(sym in child_name for sym in ['@', '#', '*'])

                if father_name in nick_style_map:
                    b_c, bg_c = nick_style_map[father_name]
                    father_display = f"<span style='color:{b_c}; background-color:{bg_c}; font-weight:bold; padding:2px 8px; border-radius:4px; border:1px solid {b_c}80;'>{father_name}</span>"
                else:
                    father_display = f"<b>{father_name}</b>"
                    
                score, badge_h = calculate_evaluation_score(child_name, is_elite_daughter=is_elite_daughter, is_high_g1=is_high_g1_son)
                
                if is_high_g1_son:
                    child_display = f"<span class='highlight-g1-son'>{child_name}</span>"
                elif is_elite_daughter:
                    child_display = f"<span class='highlight-elite-daughter'>{child_name}</span>"
                elif '-' in child_name and is_daughter:
                    child_display = f"<span class='highlight-dash-mare'>{child_name}</span>"
                else:
                    child_display = child_name

                st.markdown(f"<div class='progeny-item'>🔗 {badge_h} [연결 자마] {child_display} (부마: {father_display}) — 가중 점수: <b>{score:.1f}점</b></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='margin-left: 25px;'><div class='gauge-container'><div class='gauge-bar' style='width: {min(score/5, 100)}%;'></div></div></div>", unsafe_allow_html=True) 
