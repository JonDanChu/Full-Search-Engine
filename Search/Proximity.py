def get_best_span(doc_infos: list[dict]) -> int:
    # find the smallest span that contains one occurrence of every query term in a single document
    # a smaller span means the terms appear closer together, which indicates a better match
    
    # If there isn't a doc_infos entry for a query term then exclude it from the search
    doc_infos = [doc for doc in doc_infos if doc is not None]

    if len(doc_infos) <= 1:
        return 0

    # each entry in position_lists is the sorted list of positions for one query term in this document
    position_lists = [sorted(doc_info["wordPosition"]) for doc_info in doc_infos]
    pointers = [0] * len(position_lists)
    best_span = None

    while True:
        current_positions = []
        for i, positions in enumerate(position_lists):
            if pointers[i] >= len(positions):
                # once any term runs out of positions, there are no more full windows to evaluate.
                return best_span if best_span is not None else 0
                
            current_positions.append(positions[pointers[i]])

        # the current window is bounded by the smallest and largest active positions across all query terms.
        current_span = max(current_positions) - min(current_positions)
        if best_span is None or current_span < best_span:
            best_span = current_span

        # advance the term with the smallest current position, this is the only move that can possibly shrink the next window
        min_index = current_positions.index(min(current_positions))
        pointers[min_index] += 1