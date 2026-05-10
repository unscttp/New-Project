from typing import List

from duckduckgo_search import DDGS


from pydantic import BaseModel, Field


class SearchInternetArgs(BaseModel):
    query: str = Field(..., description="要搜索的互联网关键词或问题。")


def search_internet(query: str) -> str:
    """使用 DuckDuckGo 执行轻量搜索并返回文本摘要。"""
    query = query.strip()
    if not query:
        raise ValueError("query 不能为空。")

    summaries: List[str] = []
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
        for index, item in enumerate(results, start=1):
            title = (item.get("title") or "").strip()
            body = (item.get("body") or "").strip()
            href = (item.get("href") or "").strip()
            summaries.append(f"{index}. {title}\n摘要: {body}\n链接: {href}")

    if not summaries:
        return f"未找到与“{query}”相关的搜索结果。"

    return "\n\n".join(summaries)
