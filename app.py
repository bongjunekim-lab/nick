import streamlit as st
import xml.etree.ElementTree as ET
import re
import os
from collections import defaultdict

def clean_name_symbols(text):
    """이름 앞의 숫자, 특수기호, 공백 제거"""
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

st.set_page_config(page_title="씨수말-외조부마 듀얼 혈통 닉 분석기", layout="wide")

st.markdown("""
    <style>
    .section-title {
        color: #111111;
        font-weight: bold;
        font-size: 1.3em;
        margin-top: 15px;
        margin-bottom: 6px;
    }
    .progeny-item {
        margin-left: 25px;
        margin-bottom: 4px;
        color: #333333;
        font-size: 1.05em;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .bms-tag {
        color: #0000FF;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_mindmap_data():
    file_path = '우수한 경주마(수말, 암말).mm'
    if not os.path.exists(file_path):
        return None, None, None, "파일을 찾을 수 없습니다."
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        id_to_text = {}
        id_to_parent_text = {}
        
        for parent in root.iter('node'):
            p_text = parent.get('TEXT', 'Unknown')
            for child in parent.findall('node'):
                c_id = child.get('ID')
                if c_id:
                    id_to_text[c_id] = child.get('TEXT', '')
                    id_to_parent_text[c_id] = p_text
                    
        return root, id_to_text, id_to_parent_text, None
    except Exception as e:
        return None, None, None, f"파일 분석 오류: {str(e)}"

# ---------------------------------------------------------
# [1관점] 씨수말 관점: target_sire가 부마로서 배출한 아들/딸 + 외조부마(어미의 아비) 추적
# ---------------------------------------------------------
def analyze_sire_perspective(root, target_sire_query, id_to_text, id_to_parent_text):
    query_norm = normalize_name(target_sire_query)
    results = [] # {'progeny': 자마명, 'dam': 어미명, 'bms': 외조부마명}

    def traverse(node):
        my_text = node.get('TEXT', '')
        # 씨수말 노드 찾기
        if query_norm in normalize_name(my_text):
            for child in node.findall('node'):
                child_text = child.get('TEXT', '')
                child_id = child.get('ID')
                
                # 자마 노드(아들/딸)
                if child_text:
                    # 선(arrowlink)으로 연결된 모마(Dam) 노드 추적
                    dam_name = "미상"
                    bms_name = "미상"
                    
                    for arrow in child.findall('arrowlink'):
                        dest_id = arrow.get('DESTINATION')
                        if dest_id in id_to_text:
                            linked_text = id_to_text[dest_id]
                            # 연결된 노드가 모마인 경우
                            dam_name = linked_text
                            # 모마의 상위 노드(어미의 아비 = 외조부마 BMS)
                            bms_name = id_to_parent_text.get(dest_id, "미상")
                            break
                            
                    results.append({
                        'progeny': child_text.strip(),
                        'dam': dam_name.strip(),
                        'bms': bms_name.strip()
                    })
                    
        for child in node.findall('node'):
            traverse(child)

    traverse(root)
    return results

# ---------------------------------------------------------
# [2관점] 외조부마 관점: target_sire의 직계 딸들이 배출한 2세대 자마 추적
# ---------------------------------------------------------
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
                    for arrow in child.findall('arrowlink'):
                        dest_id = arrow.get('DESTINATION')
                        if dest_id in id_to_text:
                            c_text = id_to_text[dest_id]
                            f_text = id_to_parent_text.get(dest_id, "미상")
                            progeny_list.append({'child': c_text, 'father': f_text})
                    if progeny_list:
                        results.append({
                            'daughter': child_text.strip(),
                            'progeny': progeny_list
                        })
        for child in node.findall('node'):
            traverse(child)

    traverse(root)
    return results

# UI 화면 구성
st.title("🐎 씨수말 & 외조부마(BMS) 2단계 혈통·닉 분석기")

root_node, id_to_text, id_to_parent_text, err = load_mindmap_data()
if err:
    st.error(err)
    st.stop()

# 사이드바
st.sidebar.header("🔍 검색 설정")
search_sire = st.sidebar.text_input("씨수말 이름을 입력하세요", value="bernardini")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔀 관점 선택 (체크박스)")
view_sire_mode = st.sidebar.checkbox("1. 씨수말(Sire) 관점 분석 (아들/딸 & 외조부마 닉)", value=True)
view_bms_mode = st.sidebar.checkbox("2. 외조부마(BMS) 관점 분석 (직계딸의 자마 & 교배부마 닉)", value=False)

if not search_sire.strip():
    st.info("👈 좌측 사이드바에 씨수말 이름을 입력하세요.")
    st.stop()

sire_clean_name = clean_name_symbols(search_sire)

# =========================================================
# 1. 씨수말(Sire) 관점 출력
# =========================================================
if view_sire_mode:
    st.subheader(f"1️⃣ 씨수말 [{sire_clean_name}] 관점 전수조사")
    st.caption("※ 해당 씨수말이 직접 배출한 아들/딸과 선으로 연결된 어미(Dam) 및 외조부마(BMS)를 분석합니다.")
    
    sire_data = analyze_sire_perspective(root_node, search_sire, id_to_text, id_to_parent_text)
    
    if not sire_data:
        st.warning("씨수말 관점 자마 데이터가 없습니다.")
    else:
        # BMS(외조부마)별 중복 집계 (Nick 추출)
        bms_counts = defaultdict(int)
        for item in sire_data:
            if item['bms'] != "미상":
                bms_counts[item['bms']] += 1
                
        nick_bms = [bms for bms, cnt in bms_counts.items() if cnt >= 2]
        
        st.markdown(f"""
        <div class='info-box'>
            <b>배출 자마 총수:</b> {len(sire_data)}두 | 
            <b>매칭된 주요 외조부마(Nick BMS):</b> <span style='color:#D32F2F; font-weight:bold;'>{len(nick_bms)}두</span>
        </div>
        """, unsafe_allow_html=True)
        
        # 외조부마(BMS) 범례
        if nick_bms:
            st.markdown("**🎨 궁합이 검증된 주요 외조부마(Nick BMS):**")
            bms_html = "<div style='display:flex; flex-wrap:wrap; gap:6px; margin-bottom:15px;'>"
            for b in nick_bms:
                bms_html += f"<span style='background-color:#E0F2F1; color:#00796B; border:1px solid #00796B; padding:3px 8px; border-radius:4px; font-weight:bold;'>{b} ({bms_counts[b]}두)</span>"
            bms_html += "</div>"
            st.markdown(bms_html, unsafe_allow_html=True)
            
        st.markdown("---")
        
        # 자마 상세 리스트 출력
        for idx, item in enumerate(sire_data, 1):
            bms_style = f"<span class='bms-tag'>[외조부마: {item['bms']}]</span>" if item['bms'] in nick_bms else f"[외조부마: {item['bms']}]"
            st.markdown(f"<div class='progeny-item'>🐴 [{idx}] <b>{item['progeny']}</b> --- 🔗 (어미: {item['dam']}) | {bms_style}</div>", unsafe_allow_html=True)

# =========================================================
# 2. 외조부마(BMS) 관점 출력
# =========================================================
if view_bms_mode:
    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    st.subheader(f"2️⃣ 외조부마(BMS) [{sire_clean_name}] 관점 분석")
    st.caption("※ 해당 씨수말의 직계 딸(종빈마)들이 배출한 자마 및 교배 부마(Father)를 분석합니다.")
    
    bms_data = analyze_bms_perspective(root_node, search_sire, id_to_text, id_to_parent_text)
    
    if not bms_data:
        st.warning("직계 딸들의 자마 데이터가 없습니다.")
    else:
        for idx, item in enumerate(bms_data, 1):
            st.markdown(f"<div class='section-title'>💎 [{idx}] {item['daughter']} (자마: {len(item['progeny'])}두)</div>", unsafe_allow_html=True)
            for p in item['progeny']:
                st.markdown(f"<div class='progeny-item'>🔗 [연결 자마] {p['child']} (부마: <b>{p['father']}</b>)</div>", unsafe_allow_html=True)
