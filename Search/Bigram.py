def has_adjacent_match(left_doc_info: dict | None, right_doc_info: dict | None) -> bool:
    if left_doc_info is None or right_doc_info is None:
        return False

    right_positions = set(right_doc_info["wordPosition"])
    for left_pos in left_doc_info["wordPosition"]:
        if left_pos + 1 in right_positions:
            return True

    return False


def get_bigram_boost(
    doc_infos: list[dict | None],
    per_match_boost: float = 0.15,
) -> float:
    boost = 0.0

    for i in range(len(doc_infos) - 1):
        if has_adjacent_match(doc_infos[i], doc_infos[i + 1]):
            boost += per_match_boost

    return boost
