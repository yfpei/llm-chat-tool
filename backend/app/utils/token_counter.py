import tiktoken


def count_tokens(messages: list[dict], provider: str) -> int:
    """Count tokens for a list of messages. Uses tiktoken for both providers."""
    if not messages:
        return 0

    # Use cl100k_base encoding (works for GPT-4, Claude approximation)
    encoding = tiktoken.get_encoding("cl100k_base")

    total = 0
    for msg in messages:
        # Each message has overhead tokens (role, formatting)
        total += 4  # approximate overhead per message
        total += len(encoding.encode(msg.get("content", "")))
        total += len(encoding.encode(msg.get("role", "")))
    total += 2  # conversation overhead
    return total
