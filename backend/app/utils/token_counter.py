def count_tokens(messages: list[dict], provider: str) -> int:
    """
    Estimate token count for messages using character-based approximation.
    Roughly 4 characters per token for English text.
    """
    if not messages:
        return 0

    total = 0
    for msg in messages:
        # Each message has overhead tokens (role, formatting)
        total += 4  # approximate overhead per message
        content = msg.get("content", "")
        role = msg.get("role", "")
        # Approximate: 4 chars = 1 token
        total += len(content) // 4
        total += len(role) // 4
    total += 2  # conversation overhead
    return total
