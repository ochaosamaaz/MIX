"""
Shared utility functions used across multiple modules.
"""


def split_message(text: str, max_length: int = 4000) -> list[str]:
    """
    Split a long message into chunks that fit Telegram's 4096 char limit.
    Splits at newline boundaries for clean formatting.

    Args:
        text: The full message text
        max_length: Maximum characters per chunk (default 4000 for safety margin)

    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # Find a good split point (newline)
        split_point = text.rfind("\n", 0, max_length)
        if split_point == -1:
            split_point = max_length

        chunks.append(text[:split_point])
        text = text[split_point:].lstrip("\n")

    return chunks
