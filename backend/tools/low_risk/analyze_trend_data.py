import json
from typing import Any, List

import pandas as pd


from pydantic import BaseModel, Field


class AnalyzeTrendDataArgs(BaseModel):
    data_json: str = Field(..., description="JSON 字符串，支持数字数组或包含数值字段的对象数组。")


def _extract_numeric_values(payload: Any) -> List[float]:
    if isinstance(payload, list):
        vals=[]
        for item in payload:
            if isinstance(item,(int,float)): vals.append(float(item))
            elif isinstance(item,dict):
                vals.extend(float(v) for v in item.values() if isinstance(v,(int,float)))
        return vals
    if isinstance(payload, dict):
        return [float(v) for v in payload.values() if isinstance(v,(int,float))]
    return []

def analyze_trend_data(data_json: str) -> str:
    """对 JSON 中的数值做基础统计。"""
    try:
        payload = json.loads(data_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"data_json 不是合法 JSON: {exc}") from exc

    values = _extract_numeric_values(payload)
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
