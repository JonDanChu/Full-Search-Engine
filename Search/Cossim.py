import math

N_CORPUS = 55393

def q_tf_idf(query_tkns: list[str], df_dict: dict) -> list[float]:
    result = []
    tkn_f = dict()
    for tkn in query_tkns:
        if tkn in tkn_f:
            tkn_f[tkn] += 1
        else:
            tkn_f[tkn] = 1

    for tkn in query_tkns:
        w_tf = 1 + math.log(int(tkn_f[tkn]))
        idf = math.log(N_CORPUS / int(df_dict[tkn]))
        result.append(w_tf * idf)

    return result

def tf_idf(doc_infos: list[dict | None]) -> list[float]:
    vec = []
    for doc_data in doc_infos:
        if doc_data is not None:
            tf = int(doc_data["tf"])
            w_tf = 1 + math.log(tf)
        else:
            w_tf = 0.0

        vec.append(w_tf)

    return vec

def normalize(vec: list[float]) -> list[float] | None:
    norm = math.sqrt(sum(value * value for value in vec))
    if norm <= 0:
        return None

    return [value / norm for value in vec]

def build_query_vector(query_tkns: list[str], df_dict: dict) -> list[float] | None:
    return normalize(q_tf_idf(query_tkns, df_dict))

def get_cossim(query_vec: list[float] | None, doc_infos: list[dict | None]) -> float:
    if query_vec is None:
        return 0.0

    d_vec = normalize(tf_idf(doc_infos))
    if d_vec is None:
        return 0.0

    return sum(query_value * doc_value for query_value, doc_value in zip(query_vec, d_vec))
