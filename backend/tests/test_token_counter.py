from app.utils.token_counter import count_tokens


def test_count_tokens_openai():
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]
    count = count_tokens(messages, provider="openai")
    assert count > 0
    assert isinstance(count, int)


def test_count_tokens_anthropic():
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]
    count = count_tokens(messages, provider="anthropic")
    assert count > 0
    assert isinstance(count, int)


def test_count_tokens_empty():
    count = count_tokens([], provider="openai")
    assert count == 0


def test_count_tokens_multiple_messages():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]
    count = count_tokens(messages, provider="openai")
    single = count_tokens([messages[0]], provider="openai")
    assert count > single
