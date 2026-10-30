"""Tests for Telegram formatting and message splitting."""

from bot.message_utils import escape_html, split_telegram_message


def test_escape_html():
    """Verify HTML special characters are escaped."""
    raw = "Apple & Google <AI> 'models' & \"agents\""
    escaped = escape_html(raw)
    assert "&amp;" in escaped
    assert "&lt;AI&gt;" in escaped


def test_split_telegram_message_small():
    """Short message should not be split."""
    msg = "This is a short message under 4096 characters."
    chunks = split_telegram_message(msg, max_length=100)
    assert len(chunks) == 1
    assert chunks[0] == msg


def test_split_telegram_message_large():
    """Large message should be cleanly split into chunks <= max_length."""
    paragraphs = [f"Section {i}: " + ("lorem ipsum " * 40) for i in range(10)]
    full_text = "\n\n".join(paragraphs)

    limit = 500
    chunks = split_telegram_message(full_text, max_length=limit)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= limit

