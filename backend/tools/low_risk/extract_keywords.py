import json
from collections import Counter


def extract_keywords(text: str, top_k: int = 8) -> str:
    """提取文本中的高频关键词（按空格分词的轻量版本）。"""
    cleaned = (text or "").strip().lower()
    if not cleaned:
        raise ValueError("text 不能为空。")
    if top_k <= 0:
        raise ValueError("top_k 必须大于 0。")

    words = [token.strip(".,!?;:()[]{}\"'`") for token in cleaned.split() if token.strip()]
    if not words:
        raise ValueError("未提取到有效词语。")

    ranking = Counter(words).most_common(top_k)
    payload = [{"keyword": word, "count": count} for word, count in ranking]
    return json.dumps({"keywords": payload}, ensure_ascii=False, indent=2)
