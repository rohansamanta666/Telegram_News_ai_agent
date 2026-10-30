"""Utilities for safe Telegram HTML formatting and message chunking."""

import html
import re
from typing import List


def escape_html(text: str) -> str:
    """Escape special HTML characters for Telegram HTML parse mode."""
    if not text:
        return ""
    return html.escape(str(text), quote=False)


def split_telegram_message(text: str, max_length: int = 3900) -> List[str]:
    """Split a formatted message into chunks <= max_length characters.
    
    Splits along double-newline or single-newline boundaries so that
    articles and formatting tags are not abruptly split mid-sentence.
    """
    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    current_chunk = []
    current_length = 0

    # Split into sections by double newline
    sections = text.split("\n\n")

    for section in sections:
        sec_len = len(section) + 2  # account for \n\n
        if current_length + sec_len <= max_length:
            current_chunk.append(section)
            current_length += sec_len
        else:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk).strip())
                current_chunk = []
                current_length = 0

            # If a single section is larger than max_length, split by single newline or sentences
            if len(section) > max_length:
                lines = section.split("\n")
                for line in lines:
                    if current_length + len(line) + 1 <= max_length:
                        current_chunk.append(line)
                        current_length += len(line) + 1
                    else:
                        if current_chunk:
                            chunks.append("\n".join(current_chunk).strip())
                            current_chunk = []
                            current_length = 0
                        # If a single line exceeds max_length, hard slice it
                        while len(line) > max_length:
                            chunks.append(line[:max_length])
                            line = line[max_length:]
                        current_chunk.append(line)
                        current_length = len(line)
            else:
                current_chunk.append(section)
                current_length = len(section)

    if current_chunk:
        chunks.append("\n\n".join(current_chunk).strip())

    return [c for c in chunks if c.strip()]

