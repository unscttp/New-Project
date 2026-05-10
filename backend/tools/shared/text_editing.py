import re
from typing import List


def parse_replace_instruction(instruction: str) -> tuple[str, str]:
    text = instruction.strip()
    if "\n---\n" in text:
        head, body = text.split("\n---\n", 1)
    else:
        lines = text.splitlines()
        if len(lines) < 2:
            raise ValueError("replace_section 模式需要 section 标题和新内容。")
        head, body = lines[0], "\n".join(lines[1:])
    section = re.sub(r"^section\s*:\s*", "", head.strip(), flags=re.IGNORECASE).strip().lstrip("#").strip()
    return section, body.strip()


def extract_md_headings(lines: List[str]) -> List[tuple[int, int, str]]:
    out=[]
    for idx,line in enumerate(lines):
        m=re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if m: out.append((idx,len(m.group(1)),m.group(2).strip()))
    return out


def edit_markdown_content(original: str, instruction: str, mode: str) -> tuple[str, List[str], int]:
    normalized = original.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if mode == "append":
        t=instruction.strip(); merged=normalized.rstrip("\n"); return (f"{merged}\n\n{t}\n" if merged else f"{t}\n"), ["__appended__"], len(t.splitlines())
    if mode == "rewrite":
        t=instruction.strip(); return f"{t}\n", ["__all__"], len(t.splitlines())
    section_name, replacement = parse_replace_instruction(instruction)
    headings = extract_md_headings(lines)
    target_index=target_level=None
    for idx, level, title in headings:
        if title.lower()==section_name.lower(): target_index, target_level=idx,level; break
    if target_index is None: raise ValueError(f"未找到 Markdown 节：{section_name}")
    end_index=len(lines)
    for idx, level, _ in headings:
        if idx>target_index and level<=target_level: end_index=idx; break
    block=[lines[target_index], *replacement.splitlines()]
    new_lines = lines[:target_index] + block + lines[end_index:]
    return "\n".join(new_lines).rstrip("\n")+"\n", [section_name], len(replacement.splitlines())
