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
    """이름 정제 및 비교용 표준화 (영문/한글 모두 대응)"""
    if not text:
        return ""
    clean = text.replace('@', '').replace('#', '').replace('*', '')
    clean = clean.replace('＠', '').replace('＃', '')
    clean = clean.replace('암)', '').replace('수)', '').replace('거)', '')
    clean = clean.replace('가.', '').replace('나.', '').replace('다.', '')
    clean = clean.split('(')[0]
    # 영어는 소문자로 변환, 한글은 그대로 유지
    if re.search(r'[a-zA-Z]', clean):
        return clean.strip().lower()
    else:
        return clean.strip()

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

# 페이지 설정
st.set_page_config(page_title="씨수말 & 외조부마(BMS) 통합 혈통 닉 분석기", layout="wide")

# CSS 스타일 정의 (원본 그대로 유지)
st.markdown("""<style> ... 원본 CSS 그대로 ... </style>""", unsafe_allow_html=True)

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
# [관점 1] 씨수말 전수조사 분석 함수
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
                    # 한글 모마도 허용
                    if (query_norm not in normalize_name(potential_dam)) and is_valid_mare(potential_dam):
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
# [관점 2] 외조부마(BMS) 관점 분석 함수 (원본 그대로 유지)
# -------------------------------------------------------------------------
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

# -------------------------------------------------------------------------
# 이후 UI 출력 부분은 원본 그대로 유지
# -------------------------------------------------------------------------
# (탭 1, 탭 2 출력 로직 동일)


