from app.services.chat_service import truncate_messages


def test_truncate_no_change_when_under_limit():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    result = truncate_messages(messages, max_tokens=200000, provider="openai")
    assert len(result) == 2


def test_truncate_removes_oldest_first():
    # Create many messages that exceed the limit
    messages = [
        {"role": "user", "content": "x " * 5000}  # ~5000 tokens each
        for _ in range(100)
    ]
    result = truncate_messages(messages, max_tokens=10000, provider="openai")
    assert len(result) < len(messages)
    # Last message should always be preserved
    assert result[-1] == messages[-1]


def test_truncate_preserves_system_message():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "x " * 5000},
        {"role": "assistant", "content": "y " * 5000},
        {"role": "user", "content": "z " * 5000},
    ]
    result = truncate_messages(messages, max_tokens=10000, provider="openai")
    # System message should always be present
    assert result[0]["role"] == "system"
