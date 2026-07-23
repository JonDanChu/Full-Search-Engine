def get_imp(doc_infos: list[dict]):
    imp = 0
    for info in doc_infos:
        
        if info is None:
            continue

        # pos_imp = info["importance"][0]
        # imp += int(pos_imp) if pos_imp is not None else 1
        
        # if info["importance"] > 3:
        #     print(info)

        imp += int(info["importance"])


    return imp if imp != 0 else 1