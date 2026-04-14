import re


def redact_sensitive_text(content: str) -> str:
    """对常见邮箱和手机号做脱敏处理。"""
    text = (content or "").strip()
    if not text:
        raise ValueError("content 不能为空。")

    masked = re.sub(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", r"\1***\2", text)
    masked = re.sub(r"\b(\+?\d{1,3})?[-.\s]?(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})\b", r"***-***-\4", masked)
    return masked
