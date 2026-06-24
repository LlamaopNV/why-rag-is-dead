from typing import AsyncIterator, Optional

import anthropic

from backend.config import settings


class AnthropicClient:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> tuple[str, int, int]:
        """Returns (response_text, input_tokens, output_tokens)."""
        kwargs: dict = {
            "model": model or settings.planner_model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)
        return (
            response.content[0].text,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

    async def stream(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[tuple[str, Optional[int], Optional[int]]]:
        """
        Yields (chunk, None, None) for each text chunk.
        Final yield is ("", input_tokens, output_tokens).
        """
        kwargs: dict = {
            "model": model or settings.main_model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        async with self.client.messages.stream(**kwargs) as stream:
            async for chunk in stream.text_stream:
                yield chunk, None, None

            final = await stream.get_final_message()
            yield "", final.usage.input_tokens, final.usage.output_tokens

    async def count_tokens(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        model: Optional[str] = None,
    ) -> int:
        """Count tokens for a message set without a full API call."""
        kwargs: dict = {
            "model": model or settings.main_model,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        # count_tokens lives on client.beta.messages in some SDK versions
        try:
            response = await self.client.messages.count_tokens(**kwargs)
        except AttributeError:
            response = await self.client.beta.messages.count_tokens(**kwargs)
        return response.input_tokens
