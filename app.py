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
st.set_page_config(page_title="특정 씨수말 모계 자손 혈통 추적기", layout="wide")

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
        margin-left: 30px;
        margin-bottom: 5px;
        color: #333333;
        font-size: 1.05em;
    }
    .premium-progeny {
        color: #D32F2F !important;
        font-weight: bold;
    }
    .star-daughter {
        color: #000000 !important;
        font-weight: 900 !important;
    }
    .sire-deep-blue-bold {
        color: #0000FF !important;
        font-weight: 900 !important;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_mindmap_data():
    """xml/mm 파일 전체 노드 데이터 및 parent-child 맵핑 데이터 로드"""
    file_path = '우수한 경주마(수말, 암말).mm'
    if not os.path.exists(file_path):
        return None, None, None, "파일을 찾을 수 없습니다."
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        id_to_text = {}
        id_to_parent_text = {}
        
        # ID-Text 및 Parent 관계 매핑
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

def normalize_name(text):
    """이름 정제 및 비교용 표준화"""
    clean = text.replace('@', '').replace('#', '').replace('*', '')
    clean = clean.replace('＠', '').replace('＃', '')
    clean = clean.replace('암)', '').replace('수)', '').replace('거)', '')
    clean = clean.replace('가.', '').replace('나.', '').replace('다.', '')
    clean = clean.split('(')[0]
    return clean.strip().lower()

def find_target_sire_daughters(root, target_sire_query, id_to_text):
    """
    특정 씨수말 검색 후:
    1조건: 마명에 '암)' 표기된 딸노드 발췌
    2조건: arrowlink(마인드맵 선)로 연결된 자마가 있는 항목만 필터링
    """
    target_query_norm = normalize_name(target_sire_query)
    results = []

    def traverse(node):
        my_text = node.get('TEXT', '')
        
        # 입력한 씨수말 노드 찾기 (부분 일치 검사)
        if target_query_norm in normalize_name(my_text):
            # 씨수말 하위 노드(자마들) 순회
            for child in node.findall('node'):
                child_text = child.get('TEXT', '')
                
                # [1조건] 마명에 '암)' 표기 포함 여부 확인
                if '암)' in child_text:
                    progeny_ids = []
                    seen_ids = set()
                    mare_pure_name = normalize_name(child_text)
                    
                    # [2조건] arrowlink(선)로 연결된 자마 ID 수집
                    for arrow in child.findall('arrowlink'):
                        dest_id = arrow.get('DESTINATION')
                        if dest_id in id_to_text:
                            if dest_id in seen_ids:
                                continue
                            dest_text = id_to_text[dest_id]
                            # 자기 자신으로 연결된 예외 데이터 제거
                            if mare_pure_name == normalize_name(dest_text):
                                continue
                            progeny_ids.append(dest_id)
                            seen_ids.add(dest_id)
                    
                    # 2조건 만족 (연결된 자마가 1두 이상 존재하는 경우에만 포함)
                    if progeny_ids:
                        results.append({
                            'sire_name': my_text.strip(),
                            'mare_name': child_text.strip(),
                            'progeny_ids': progeny_ids
                        })
                        
        for child in node.findall('node'):
            traverse(child)

    traverse(root)
    return results

# UI 타이틀
st.title("🐎 씨수말 모계(BMS) 혈통 추적 및 중복 교배(Nick) 분석기")

root_node, id_to_text, id_to_parent_text, err = load_mindmap_data()
if err:
    st.error(err)
    st.stop()

# 사이드바 설정
st.sidebar.header("🔍 씨수말 검색 설정")
search_sire = st.sidebar.text_input("씨수말 이름을 입력하세요", placeholder="예: 디프임팩트, 딥임팩트 등")

if not search_sire.strip():
    st.info("👈 좌측 사이드바에 검색하고 싶은 씨수말 이름을 입력해 주세요.")
    st.stop()

# 데이터 조회
search_results = find_target_sire_daughters(root_node, search_sire, id_to_text)

if not search_results:
    st.warning(f"'{search_sire}'(으)로 검색된 조건 [암) 표기 + 선(arrowlink) 연결 자마 보유] 만족 데이터가 없습니다.")
    st.stop()

# -------------------------------------------------------------
# [3조건] 교배 부마(Father)들의 등장 횟수를 미리 집계하여 중복 부마 식별 및 배경색 매핑
# -------------------------------------------------------------
father_counts = defaultdict(int)
g1_pattern = re.compile(r'G1-(\d+)')

for item in search_results:
    for p_id in item['progeny_ids']:
        father_name = id_to_parent_text.get(p_id, "정보 없음")
        father_counts[father_name] += 1

# 2회 이상 중복 등장한 부마(Nick Sires)
nick_sires = [father for father, count in father_counts.items() if count >= 2 and father != "정보 없음"]

# 파스텔톤 팔레트 설정 (기존 코드 디자인 보존)
bg_palette = ["#FFEBEE", "#E0F2F1", "#F3E5F5", "#E8F5E9", "#FBE9E7", "#FFFDE7", "#E1F5FE"]
border_palette = ["#D32F2F", "#00796B", "#7B1FA2", "#388E3C", "#E64A19", "#FBC02D", "#0288D1"]

nick_style_map = {}
for idx, ns in enumerate(nick_sires):
    nick_style_map[ns] = (border_palette[idx % len(border_palette)], bg_palette[idx % len(bg_palette)])

# 상단 결과 요약 뷰
st.markdown(f"""
<div class='info-box'>
    <b>검색 키워드:</b> <span style='color:#0077CC;'>{search_sire}</span> | 
    <b>조건 충족 딸(암말):</b> 총 {len(search_results)}두 | 
    <b>중복 교배(Nick) 부마 수:</b> <span style='color:#D32F2F;'>{len(nick_sires)}두</span>
</div>
""", unsafe_allow_html=True)

# 중복 교배 부마 범례(Legend) 표시
if nick_sires:
    st.subheader("🎨 중복 교배 부마(Nick) 하이라이트 범례")
    legend_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;'>"
    for ns in nick_sires:
        b_c, bg_c = nick_style_map[ns]
        cnt = father_counts[ns]
        legend_html += f"<span style='background-color:{bg_c}; color:{b_c}; border:1px solid {b_c}; font-weight:bold; padding:4px 10px; border-radius:6px; font-size:0.9em;'>{ns} ({cnt}두)</span>"
    legend_html += "</div>"
    st.markdown(legend_html, unsafe_allow_html=True)

st.markdown("---")

# 리스트 출력 영역
for idx, item in enumerate(search_results, 1):
    mare_name = item['mare_name']
    progeny_ids = item['progeny_ids']
    
    st.markdown(f"<div class='elite-mare'>💎 [{idx}] {mare_name} (연결 자마: {len(progeny_ids)}두)</div>", unsafe_allow_html=True)
    
    for p_id in progeny_ids:
        child_name = id_to_text.get(p_id, "")
        father_name = id_to_parent_text.get(p_id, "정보 없음")
        
        # 자마 텍스트 스타일링
        g1_match = g1_pattern.search(child_name)
        is_high_g1 = bool(g1_match and int(g1_match.group(1)) >= 7)
        is_daughter = '암)' in child_name
        is_elite_daughter = ('@' in child_name or '#' in child_name or '＠' in child_name or '＃' in child_name) and is_daughter
        is_high_g1_son = is_high_g1 and not is_daughter
        
        if is_high_g1_son or is_elite_daughter:
            child_display = f"<span class='premium-progeny'>{child_name}</span>"
        elif '*' in child_name and is_daughter:
            child_display = f"<span class='star-daughter'>{child_name}</span>"
        else:
            child_display = child_name

        # [3조건 적용] 부마 스타일링 (중복 부마는 색상 배경 박스 적용)
        if father_name in nick_style_map:
            b_c, bg_c = nick_style_map[father_name]
            father_display = f"<span style='color:{b_c}; background-color:{bg_c}; font-weight:bold; padding:2px 8px; border-radius:4px; border:1px solid {b_c}80;'>{father_name}</span>"
        else:
            father_display = f"<b>{father_name}</b>"
            
        st.markdown(f"<div class='progeny-item'>🔗 [연결 자마] {child_display} (부마: {father_display})</div>", unsafe_allow_html=True)
