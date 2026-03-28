"""笔记页：转录原文富文本（时间戳 / speaker 区分样式）。"""

from __future__ import annotations

import html
import re

# 时间范围 [MM:SS–MM:SS] 或 [H:MM:SS–H:MM:SS]（支持 - 与 –）
_RE_TIME_RANGE = re.compile(
    r"(\[[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?\s*[–-]\s*[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?\])"
)
_RE_SPEAKER = re.compile(r"(\[speaker_[^\]]+\])")


def transcript_plain_to_html(text: str) -> str:
    """将纯文本转录转为 HTML：时间戳、说话人标签与正文区分颜色。"""
    if not text.strip():
        return "<p style='color:#8a93a3;'>（无内容）</p>"

    blocks: list[str] = []
    for line in text.split("\n"):
        esc = html.escape(line)
        esc = _RE_TIME_RANGE.sub(
            r'<span style="color:#5eb3c9;font-size:12px;font-family:Consolas,\'SF Mono\',monospace;">\1</span>',
            esc,
        )
        esc = _RE_SPEAKER.sub(
            r'<span style="color:#b89fd4;font-weight:600;">\1</span>',
            esc,
        )
        blocks.append(esc)

    body = "<br/>".join(blocks)
    return (
        '<div style="color:#dfe6f0;font-size:14px;line-height:1.75;">'
        f"{body}</div>"
    )
