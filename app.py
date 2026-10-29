def analyze_sire_perspective(root, target_sire_query, id_to_text, id_to_parent_text, id_to_node, parent_to_children):
    query_norm = normalize_name(target_sire_query)
    results = []

    forward_arrows = defaultdict(list)
    backward_arrows = defaultdict(list)
    
    # 전체 노드의 부모를 역으로 찾기 위한 맵핑 생성 (child_id -> parent_node)
    child_to_parent_node = {}
    for parent in root.iter('node'):
        for child in parent.findall('node'):
            child_to_parent_node[child.get('ID')] = parent

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

                # 1. 자마(child)에서 연결된 화살표(모마) 찾기
                if child_id in forward_arrows:
                    for d_id in forward_arrows[child_id]:
                        if d_id in id_to_text:
                            txt = id_to_text[d_id]
                            if '암)' in txt or '무전적' in txt:
                                target_dam_id = d_id
                                break
                if not target_dam_id and child_id in backward_arrows:
                    for d_id in backward_arrows[child_id]:
                        if d_id in id_to_text:
                            txt = id_to_text[d_id]
                            if '암)' in txt or '무전적' in txt:
                                target_dam_id = d_id
                                break

                # 화살표로 못 찾았으면 노드의 부모 텍스트 확인
                if not target_dam_id:
                    parent_text = id_to_parent_text.get(child_id, "")
                    if parent_text and ('암)' in parent_text or '무전적' in parent_text):
                        dam_name = parent_text
                
                if target_dam_id and target_dam_id in id_to_text:
                    potential_dam = id_to_text[target_dam_id]
                    if normalize_name(child_text) != normalize_name(potential_dam):
                        dam_name = potential_dam

                        # 2. 외조부마(BMS) 정확한 추적: 모마 노드의 '부모 노드'가 곧 외조부마임
                        dam_parent_node = child_to_parent_node.get(target_dam_id)
                        if dam_parent_node is not None:
                            p_text = dam_parent_node.get('TEXT', '')
                            # 외조부마는 암말이 아니어야 함 ('암)'이 포함되지 않고, 씨수말 계보 상의 이름이어야 함)
                            if p_text and '암)' not in p_text and query_norm not in normalize_name(p_text):
                                bms_name = p_text

                # 만약 계층 구조로 못 찾았을 경우 기존 부모 정보 대비책 활용
                if bms_name == "미상" and target_dam_id:
                    p_bms = id_to_parent_text.get(target_dam_id, "미상")
                    if p_bms and p_bms != "Unknown" and '암)' not in p_bms and query_norm not in normalize_name(p_bms):
                        bms_name = p_bms

                # 자기 참조 방어
                if normalize_name(child_text) == normalize_name(dam_name):
                    dam_name = "미상"
                if normalize_name(child_text) == normalize_name(bms_name):
                    bms_name = "미상"

                cleaned_dam = clean_and_normalize_text(dam_name)
                cleaned_bms = clean_and_normalize_text(bms_name)

                results.append({
                    'progeny': child_text.strip(),
                    'dam': cleaned_dam if cleaned_dam else "미상",
                    'bms': cleaned_bms if cleaned_bms else "미상"
                })

        for child in node.findall('node'):
            traverse(child)

    traverse(root)
    return results
