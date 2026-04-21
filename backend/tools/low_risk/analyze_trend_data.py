import json
from typing import Any, Callable, List

import pandas as pd


def analyze_trend_data(data_json: str, *, extract_numeric_values: Callable[[Any], List[float]]) -> str:
    """对 JSON 中的数值做基础统计。"""
    try:
        payload = json.loads(data_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"data_json 不是合法 JSON: {exc}") from exc

    values = extract_numeric_values(payload)
    if not values:
        raise ValueError("未从 data_json 中提取到可分析的数值。")

    series = pd.Series(values, dtype="float64")
    result = {
        "count": int(series.count()),
        "mean": round(float(series.mean()), 4),
        "max": round(float(series.max()), 4),
        "min": round(float(series.min()), 4),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
