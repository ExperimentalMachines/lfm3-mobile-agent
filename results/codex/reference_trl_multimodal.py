# Evidence excerpt: https://github.com/huggingface/trl/blob/v1.16.0/trl/data_utils.py
# Git blob: 908cd98379e24284ffa9407c730782a8c263b464
# Copyright 2020-2026 The HuggingFace Team. Licensed under Apache-2.0.
# https://www.apache.org/licenses/LICENSE-2.0
from __future__ import annotations

def prepare_multimodal_messages(messages: list[dict[str, Any]], images: list | None = None) -> list[dict[str, Any]]:
    # docstyle-ignore  # because <Image> is not parsable in the code block
    """
    Convert messages into a structured multimodal format and inject the provided images into the message contents.

    Args:
        messages (`list[dict[str, Any]]`):
            Messages with `"role"`, `"content"` (or `"tool_calls"`). Content may be a raw string before transformation.
            List of messages with a `"role"` key (`"system"`, `"user"`, `"assistant"`, or `"tool"`) and a `"content"` key containing
            either a string or a list of structured blocks if already prepared. Optionally, the `"content"` might
            be `None` or not provided in favour of `"tool_calls"` in the `"assistant"` turns if applicable.
        images (`list`, *optional*):
            List of image objects to insert in the messages.

    Returns:
        `list[dict[str, Any]]`: A new list of messages where every `"content"` value is a list of structured
        content blocks, and all `"image"` placeholders are populated with the corresponding image objects. If the
        assistant turns contains `"tool_calls"`, then the `"content"` might be empty.

    Notes:
        - When the input `messages` isn't already in the structured format, (i.e., all `"content"` values are strings),
          the function transforms them into the structured format by wrapping text in `{"type": "text", "text": ...}`
          and inserting `{"type": "image"}` placeholders for the images *before* the first user message.
          If the number of placeholders does not match the number of provided images, an error is raised.
        - Existing image blocks that already include an `"image"` payload are preserved as-is. Only unfilled image
          placeholders are counted and populated from `images`.

    Example:
    ```python
    # Input
    [
        {"role": "user", "content": "What's in this image?"},
        {"role": "assistant", "content": "It looks like a cat."},
    ]

    # Output, one image provided
    [
        {"role": "user", "content": [{"type": "image", "image": <PIL.Image.Image>}, {"type": "text", "text": "What's in this image?"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "It looks like a cat."}]},
    ]
    ```
    """
    images = images or []

    # First, convert all messages to the structured format if needed, and insert image placeholders if needed.
    # Build new message dicts only when transforming string content to avoid modifying the originals.
    new_messages = []
    images_included = False
    for message in messages:
        if message["role"] == "user":
            if isinstance(message["content"], str) and not images_included:
                image_entries = [{"type": "image"} for _ in range(len(images))]
                message = {**message, "content": [*image_entries, {"type": "text", "text": message["content"]}]}
                images_included = True
            elif isinstance(message["content"], str):
                message = {**message, "content": [{"type": "text", "text": message["content"]}]}
        elif message["role"] in {"assistant", "system", "tool"}:
            if isinstance(message.get("content"), str):
                message = {**message, "content": [{"type": "text", "text": message["content"]}]}
        else:
            raise ValueError(
                f"Invalid role in message: {message['role']}. Expected 'system', 'user', 'assistant', or 'tool'."
            )
        new_messages.append(message)

    # Then, check that the number of image placeholders matches the number of images provided
    num_placeholders = sum(
        sum(1 for part in message["content"] if part["type"] == "image" and "image" not in part)
        for message in new_messages
        if message.get("content") and message["role"] != "tool"
    )
    if num_placeholders != len(images):
        raise ValueError(
            f"Number of images provided ({len(images)}) does not match number of image placeholders ({num_placeholders})."
        )

    # Then, fill in the actual images in the placeholders
    if images:
        img_idx = 0
        for i, message in enumerate(new_messages):
            if not message.get("content") or message["role"] == "tool":
                continue
            new_content = []
            for part in message["content"]:
                if part["type"] == "image" and "image" not in part:
                    new_content.append({**part, "image": images[img_idx]})
                    img_idx += 1
                else:
                    new_content.append(part)
            new_messages[i] = {**message, "content": new_content}

    return new_messages


