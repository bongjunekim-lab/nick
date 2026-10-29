import streamlit as st
import xml.etree.ElementTree as ET
import re
import os
from collections import defaultdict

def clean_name_symbols(text):
    """씨수말 이름 맨 앞의 숫자, 특수기호(도형, 기호 등), 공백을 모두 제거합니다."""
    cleaned = re.sub(r'^[\d\s\W_]+', '', text)
    return cleaned.strip()

# 1. 페이지 설정
st.set_page_config(page_title="엘리트 혈통 추적 시스템", layout="wide")

# CSS 설정
st.markdown("""
    <style>
    .elite-mare {
        color: #0077CC !important;
        font-weight: bold;
        font-size: 1.25em;
        margin-top: 10px;
        margin-bottom: 4px;
    }
    .progeny-item {
        margin-left: 30px;
        margin-bottom: 3px;
        color: #333333;
        font-size: 1.05em;
    }
    /* G1-7 수말 및 @, # 암말 강조 (적색 기본) */
    .premium-progeny {
        color: #D32F2F !important;
        font-weight: bold;
    }
    /* 요청사항: 암말 @, #, * 기호가 있는 경우 진한 파란색 (#0000FF) 강조 */
    .highlight-elite-daughter {
        color: #0000FF !important;
        font-weight: 900 !important;
    }
    .star-daughter {
        color: #000000 !important;
        font-weight: 900 !important;
    }
    /* 요청사항: 수말인 경우 G1-7두 이상 배출 자마는 진한 파란색 (#0000FF) 강조 */
    .highlight-g1-son {
        color: #0000FF !important;
        font-weight: 900 !important;
    }
    .sire-deep-blue-bold {
        color: #0000FF !important;
        font-weight: 900 !important;
    }
    .hr-line {
        margin: 10px 0;
        border-bottom: 1px solid #ddd;
    }
    
    /* 아코디언(expander) 헤더 폰트 크기 및 굵기 조정 */
    div[data-testid="stExpander"] summary p {
        font-size: 1.2em !important; 
        font-weight: 400 !important; 
        color: #111111 !important;
    }
    
    /* 랭킹 타이틀 내 강조된 통산 점수를 부마와 동일한 진한 파란색(#0000FF)으로 강제 덮어쓰기 */
    div[data-testid="stExpander"] summary p span,
    div[data-testid="stExpander"] summary p strong {
        color: #0000FF !important;
        font-weight: 900 !important;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def parse_bloodline_data():
    file_path = '우수한 경주마(수말, 암말).mm'
    if not os.path.exists(file_path):
        return None, None, None, "파일을 찾을 수 없습니다."
    try:
        tree = ET.parse(file_path); root = tree.getroot()
        id_to_text = {}; id_to_parent_text = {}
        for parent in root.iter('node'):
            p_text = parent.get('TEXT', 'Unknown')
            for child in parent.findall('node'):
                c_id = child.get('ID')
                if c_id:
                    id_to_text[c_id] = child.get('TEXT', '')
                    id_to_parent_text[c_id] = p_text
        year_pattern = re.compile(r'(\d{4})')
        elite_sire_map = defaultdict(list)
        
        def normalize_name(text):
            clean = text.replace('@', '').replace('#', '').replace('*', '')
            clean = clean.replace('＠', '').replace('＃', '')
            clean = clean.replace('암)', '').replace('수)', '').replace('거)', '')
            clean = clean.replace('가.', '').replace('나.', '').replace('다.', '')
            clean = clean.split('(')[0]
            return clean.strip().lower()
            
        def traverse(node, parent_text="Unknown"):
            my_text = node.get('TEXT', '')
            if my_text and ('@' in my_text or '#' in my_text or '＠' in my_text or '＃' in my_text):
                year_match = year_pattern.search(my_text)
                birth_year = int(year_match.group(1)) if year_match else 0
                progeny_info = []; seen_ids = set()
                mare_pure_name = normalize_name(my_text)
                for arrow in node.findall('arrowlink'):
                    dest_id = arrow.get('DESTINATION')
                    if dest_id in id_to_text:
                        if dest_id in seen_ids: continue
                        child_raw_text = id_to_text[dest_id]
                        child_pure_name = normalize_name(child_raw_text)
                        if mare_pure_name == child_pure_name: continue
                        progeny_info.append(dest_id)
                        seen_ids.add(dest_id)
                mare_info = {'name': my_text.strip(), 'year': birth_year, 'progeny_ids': progeny_info}
                if parent_text != "Unknown": 
                    if normalize_name(parent_text) != mare_pure_name:
                        elite_sire_map[parent_text.strip()].append(mare_info)
            for child in node.findall('node'): traverse(child, my_text)
        traverse(root); return elite_sire_map, id_to_text, id_to_parent_text, None
    except Exception as e: return None, None, None, f"분석 오류: {str(e)}"

# UI 메인
st.title("🐎 암말우성 씨수말 랭킹과 점수")

password = st.text_input("접속 암호를 입력하세요", type="password")

if password != "5500":
    st.markdown("""
    <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #d32f2f; margin-top: 10px; margin-bottom: 20px;'>
        <h4 style='margin-top: 0; color: #333;'>📢 업데이트 소식 및 이용 안내</h4>
        <ul style='margin-bottom: 0; color: #555; line-height: 1.7; font-size: 1.05em;'>
            <li><b>[기능 추가]</b> BMS(외조부)의 유전력을 기준으로 점수화 시스템을 도입했습니다. 좌측 사이드바의 <b>현구간 최소 점수 필터(Cut-off)</b>를 통해 원하는 기준 이상의 씨수말만 필터링할 수 있습니다. (기본값 3.0점)</li>
            <li><b>[특수 강조]</b> 닉스 정밀 분석을 위해 암말의 <span style='color: #0000FF; font-weight: bold;'>@, #, * 기호</span> 및 수말의 <span style='color: #0000FF; font-weight: bold;'>G1-7두 이상 배출</span> 자마에 진한 파란색 강조 기능을 추가했습니다.</li>
            <li><b>[문의처]</b> bongjunekim@gmail.com / 010-8982-3811(문자 요망)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    if password: 
        st.error("암호 오류")
    st.stop()

# --- 로그인 후 초슬림 공지사항 노출 ---
with st.expander("📢 업데이트 소식 및 이용 안내 (클릭하여 펴기)"):
    st.markdown("""
    <ul style='margin-bottom: 0; color: #555; line-height: 1.6; font-size: 0.95em;'>
        <li><b>[특수 강조 추가]</b> 암말(@, #, *) 및 수말(G1-7두 이상) 진한 파란색 하이라이트 옵션 제공</li>
        <li><b>[문의처]</b> bongjunekim@gmail.com / 010-8982-3811(문자 요망)</li>
    </ul>
    """, unsafe_allow_html=True)

elite_map, id_to_text, id_to_parent_text, err = parse_bloodline_data()
if err: st.error(err); st.stop()

# 좌측 사이드바 필터 설정 영역
st.sidebar.markdown("### 🔍 검색 조건 설정")
start_y, end_y = st.sidebar.slider("종빈마 출생 연도 필터", 1900, 2030, (1900, 2026))

st.sidebar.markdown("---")
sire_start_y, sire_end_y = st.sidebar.slider("씨수말 출생 연도 필터", 1900, 2030, (1900, 2026))

st.sidebar.markdown("---")
min_score = st.sidebar.slider("현구간 최소 점수 필터", 0.0, 30.0, 3.0, 0.5)

st.sidebar.markdown("---")
show_sire_bms = st.sidebar.checkbox("혈통상 모계 깊이(부마 BMS) 보기", value=False)

st.sidebar.markdown("---")
# 요청하신 조건에 따른 하이라이트 토글 체크박스 추가
highlight_special_progeny = st.sidebar.checkbox("🎯 특수 자마 하이라이트 (암말 @,#,* & 수말 G1-7+ 파란색 강조)", value=True)

st.sidebar.markdown("---")
show_undervalued_bms = st.sidebar.checkbox("저평가 우량 BMS (Undervalued BMS)", value=False)
if show_undervalued_bms:
    st.sidebar.caption("※ 부마로서 G1 우승 자마를 6두 이하로 배출했거나 없는(GX) 씨수말만 표시합니다.")

g1_pattern = re.compile(r'G1-(\d+)')

def calculate_score(daughters_list):
    n1 = len(daughters_list)
    s2 = 0
    n2 = 0
    
    for d in daughters_list:
        for p_id in d['progeny_ids']:
            child_name = id_to_text.get(p_id, "")
            g1_match = g1_pattern.search(child_name)
            is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
            is_daughter = '암)' in child_name
            
            is_n2 = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name) and is_daughter
            is_s2 = is_high_g1 and not is_daughter
            
            if is_n2: n2 += 1
            if is_s2: s2 += 1
            
    score = (10.0 * n1) + (15.0 * s2) + (20.0 * n2)
    return score

sire_all_bms_scores = {}
for sire, all_daughters in elite_map.items():
    sire_clean_key = sire.strip()
    filtered_d = [d for d in all_daughters if start_y <= d['year'] <= end_y]
    all_time_s = calculate_score(all_daughters)
    current_s = calculate_score(filtered_d) if filtered_d else 0.0
    if all_time_s > 0:
        sire_all_bms_scores[sire_clean_key] = (current_s, all_time_s)

scored_results = []
year_pattern = re.compile(r'(\d{4})')

for sire, all_daughters in elite_map.items():
    sire_year_match = year_pattern.search(sire)
    sire_year = int(sire_year_match.group(1)) if sire_year_match else 0
    
    if sire_year > 0 and not (sire_start_y <= sire_year <= sire_end_y):
        continue
    
    if show_undervalued_bms:
        is_gx = bool(re.search(r'G\s*X', sire))
        g1_sire_match = re.search(r'G\s*1\s*-\s*(\d+)', sire)
        if not is_gx:
            if g1_sire_match:
                if int(g1_sire_match.group(1)) > 6: continue
            else: continue

    filtered_daughters = [d for d in all_daughters if start_y <= d['year'] <= end_y]
    if not filtered_daughters: continue
        
    all_time_score = calculate_score(all_daughters)
    n1 = len(filtered_daughters)
    filtered_score = calculate_score(filtered_daughters)
    
    if filtered_score >= min_score:
        scored_results.append({
            'sire': sire,
            'daughters': filtered_daughters,
            'n1': n1,
            'score': filtered_score,
            'all_time_score': all_time_score
        })

scored_results.sort(key=lambda x: x['score'], reverse=True)

if not scored_results: 
    st.warning("조건에 맞는 데이터가 없습니다. 사이드바의 필터 조건을 조정해 보세요.")
else:
    for i, data in enumerate(scored_results[:500], 1):
        sire = data['sire']
        daughters = data['daughters']
        n1 = data['n1']
        score = data['score']
        all_time_score = data['all_time_score']
        stars = "⭐" * n1
        
        display_sire = clean_name_symbols(sire)
        
        if (all_time_score - score) >= 3.0:
            all_time_str = f":blue[**(통산: {all_time_score:.1f}점)**]"
        else:
            all_time_str = f"(통산: {all_time_score:.1f}점)"
        
        expander_title = f"[{i}위] {display_sire} (엘리트 종빈마: {n1}두) {stars} | 🏆 현구간: {score:.1f}점 {all_time_str}"
        
        with st.expander(expander_title):
            sire_to_mothers = defaultdict(set)
            for d in daughters:
                for p_id in d['progeny_ids']:
                    p_sire_name = id_to_parent_text.get(p_id, "정보 없음")
                    sire_to_mothers[p_sire_name].add(d['name'])
            nick_sires = [s for s, mothers in sire_to_mothers.items() if len(mothers) >= 2]
            bg_palette = ["#FFEBEE", "#E0F2F1", "#F3E5F5", "#E8F5E9", "#FBE9E7"]
            border_palette = ["#D32F2F", "#00796B", "#7B1FA2", "#388E3C", "#E64A19"]
            nick_style_map = {}
            color_idx = 0
            for ns in nick_sires:
                nick_style_map[ns] = (border_palette[color_idx % 5], bg_palette[color_idx % 5])
                color_idx += 1

            for d in daughters:
                st.markdown(f"<div class='elite-mare'>&#128142; {d['name']}</div>", unsafe_allow_html=True)
                
                if d['progeny_ids']:
                    for p_id in d['progeny_ids']:
                        child_name = id_to_text.get(p_id, "")
                        father_name = id_to_parent_text.get(p_id, "정보 없음")
                        
                        g1_match = g1_pattern.search(child_name)
                        is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
                        is_daughter = '암)' in child_name
                        
                        # 암말 기호 확인 (@, #, ＠, ＃, *)
                        is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name or '*' in child_name) and is_daughter
                        # 수말 G1-7 이상 확인
                        is_high_g1_son = is_high_g1 and not is_daughter
                        
                        # 스타일 적용 (체크박스가 켜져 있을 때만 진한 파란색 강조 적용)
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
                            elif '*' in child_name and is_daughter:
                                child_display = f"<span class='star-daughter'>{child_name}</span>"
                            else: 
                                child_display = child_name
                        
                        bms_depth_text = ""
                        clean_father_name = father_name.strip()
                        if show_sire_bms and clean_father_name in sire_all_bms_scores:
                            cur_s, all_s = sire_all_bms_scores[clean_father_name]
                            bms_depth_text = f"&nbsp;&nbsp;&nbsp;<span style='color:#000000; font-weight:normal; font-size:0.95em;'>[BMS 현구간: {cur_s:.1f}점, 통산 점수: {all_s:.1f}점]</span>"

                        if is_high_g1_son or is_elite_daughter:
                            if father_name in nick_style_map:
                                b_c, bg_c = nick_style_map[father_name]
                                father_display = f"<span style='color:#0000FF; background-color:{bg_c}; font-weight:900; padding:2px 6px; border-radius:4px; border: 1px solid {b_c}60;'>{father_name}</span>{bms_depth_text}"
                            else:
                                father_display = f"<span class='sire-deep-blue-bold'>{father_name}</span>{bms_depth_text}"
                        else:
                            if father_name in nick_style_map:
                                b_c, bg_c = nick_style_map[father_name]
                                father_display = f"<span style='color:{b_c}; background-color:{bg_c}; font-weight:400; padding:2px 6px; border-radius:4px; border: 1px solid {b_c}60;'>{father_name}</span>{bms_depth_text}"
                            else: 
                                father_display = f"<b>{father_name}</b>{bms_depth_text}"
                        
                        st.markdown(f"<div class='progeny-item'>🔗 [연결] {child_display} ({father_display})</div>", unsafe_allow_html=True)
