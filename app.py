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

st.set_page_config(page_title="씨수말-외조부마 2단계 혈통 닉 분석기", layout="wide")

st.markdown("""
    <style>
    .progeny-item {
        margin-left: 20px;
        margin-bottom: 5px;
        color: #333333;
        font-size: 1.05em;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .bms-highlight {
        color: #0000FF;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_mindmap_data():
    file_path = '우수한 경주마(수말, 암말).mm'
    if not os.path.exists(file_path):
        return None, None, None, None, "파일을 찾을 수 없습니다."
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        id_to_text = {}
        id_to_parent_text = {}
        id_to_node = {}
        
        # 전체 노드 및 부모-자식 관계 인덱싱
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

# ---------------------------------------------------------
# [1관점 핵심 로직] 정방향/역방향 arrowlink 및 트리 구조 양방향 전체 탐색
# ---------------------------------------------------------
def analyze_sire_perspective(root, target_sire_query, id_to_text, id_to_parent_text, id_to_node):
    query_norm = normalize_name(target_sire_query)
    results = []

    # 1. 전체 마인드맵에서 화살표(arrowlink) 맵 구축 (출발 ID -> 도착 ID, 도착 ID -> 출발 ID)
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

    def find_dam_and_bms(child_node, child_id):
        dam_name = "미상"
        bms_name = "미상"

        # [방식 A] 자마 노드에서 출발하는 arrowlink 선 추적 (자마 -> 모마)
        target_dam_id = None
        if child_id in forward_arrows:
            target_dam_id = forward_arrows[child_id][0]
        # [방식 B] 모마 노드에서 자마 노드로 들어오는 arrowlink 역추적 (모마 -> 자마)
        elif child_id in backward_arrows:
            target_dam_id = backward_arrows[child_id][0]

        if target_dam_id and target_dam_id in id_to_text:
            dam_name = id_to_text[target_dam_id]
            # 모마의 상위 트리 노드 = 외조부마(BMS)
            bms_name = id_to_parent_text.get(target_dam_id, "미상")
            return dam_name, bms_name

        # [방식 C] arrowlink 선이 없는 경우: 트리 구조상 상위 노드가 모마인지 확인
        parent_text = id_to_parent_text.get(child_id, "미상")
        if parent_text != "미상" and normalize_name(parent_text) != query_norm:
            dam_name = parent_text
            # 모마 노드의 ID 찾기
            for p_id, p_text in id_to_text.items():
                if p_text == parent_text:
                    bms_name = id_to_parent_text.get(p_id, "미상")
                    break

        return dam_name, bms_name

    # 씨수말 노드 탐색 및 하위 자마 추적
    def traverse(node):
        my_text = node.get('TEXT', '')
        if query_norm in normalize_name(my_text):
            for child in node.findall('node'):
                child_text = child.get('TEXT', '')
                child_id = child.get('ID')
                if not child_text:
                    continue

                dam_name, bms_name = find_dam_and_bms(child, child_id)
                
                results.append({
                    'progeny': child_text.strip(),
                    'dam': dam_name.strip(),
                    'bms': bms_name.strip()
                })

        for child in node.findall('node'):
            traverse(child)

    traverse(root)
    return results

# UI 화면 구성
st.title("🐎 씨수말 & 외조부마(BMS) 2단계 혈통·닉 분석기")

root_node, id_to_text, id_to_parent_text, id_to_node, err = load_mindmap_data()
if err:
    st.error(err)
    st.stop()

# 사이드바
st.sidebar.header("🔍 검색 설정")
search_sire = st.sidebar.text_input("씨수말 이름을 입력하세요", value="bernardini")

if not search_sire.strip():
    st.info("👈 좌측 사이드바에 씨수말 이름을 입력하세요.")
    st.stop()

sire_clean_name = clean_name_symbols(search_sire)

st.subheader(f"1️⃣ 씨수말 [{sire_clean_name}] 관점 전수조사")
st.caption("※ 자마와 연결된 선(arrowlink)을 정방향/역방향으로 추적하여 모마(Dam)와 외조부마(BMS)를 정밀 매칭합니다.")

sire_data = analyze_sire_perspective(root_node, search_sire, id_to_text, id_to_parent_text, id_to_node)

if not sire_data:
    st.warning("조건에 맞는 자마 데이터가 없습니다.")
else:
    # 2회 이상 매칭된 주요 외조부마(Nick BMS) 집계
    bms_counts = defaultdict(int)
    for item in sire_data:
        if item['bms'] != "미상":
            bms_counts[item['bms']] += 1
            
    nick_bms = [bms for bms, cnt in bms_counts.items() if cnt >= 2]
    
    st.markdown(f"""
    <div class='info-box'>
        <b>배출 자마 총수:</b> {len(sire_data)}두 | 
        <b>중복 매칭된 외조부마(Nick BMS):</b> <span style='color:#D32F2F; font-weight:bold;'>{len(nick_bms)}두</span>
    </div>
    """, unsafe_allow_html=True)
    
    if nick_bms:
        st.markdown("**🎨 주요 외조부마(Nick BMS) 범례:**")
        bms_html = "<div style='display:flex; flex-wrap:wrap; gap:6px; margin-bottom:15px;'>"
        for b in nick_bms:
            bms_html += f"<span style='background-color:#E0F2F1; color:#00796B; border:1px solid #00796B; padding:3px 8px; border-radius:4px; font-weight:bold;'>{clean_name_symbols(b)} ({bms_counts[b]}두)</span>"
        bms_html += "</div>"
        st.markdown(bms_html, unsafe_allow_html=True)
        
    st.markdown("---")
    
    for idx, item in enumerate(sire_data, 1):
        bms_display = clean_name_symbols(item['bms'])
        dam_display = clean_name_symbols(item['dam'])
        
        if item['bms'] in nick_bms:
            bms_style = f"<span class='bms-highlight'>[외조부마: {bms_display}]</span>"
        else:
            bms_style = f"[외조부마: {bms_display}]"
            
        st.markdown(f"<div class='progeny-item'>🐴 [{idx}] <b>{item['progeny']}</b> --- 🔗 (모마: {dam_display}) | {bms_style}</div>", unsafe_allow_html=True)
