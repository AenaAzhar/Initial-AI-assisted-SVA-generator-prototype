"""Wrapper around the Claude API.

Handles structured-output parsing, retry on transient errors, and
configuration via environment variables.
"""

import json
import os
import time
from dataclasses import dataclass

from anthropic import Anthropic, APIError
from dotenv import load_dotenv

from sva_gen.prompts import SYSTEM_PROMPT, build_messages

load_dotenv()


@dataclass
class Property:
    name: str
    description: str
    kind: str  # assert | cover | assume
    sva_code: str
    justification: str


@dataclass
class GenerationResult:
    module_name: str
    summary: str
    clock_signal: str
    reset_signal: str
    properties: list[Property]
    notes: str
    raw_response: str  # for debugging


class LLMClient:
    def __init__(self, model: str | None = None, max_retries: int = 3):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill it in."
            )
        self.client = Anthropic(api_key=api_key)
        self.model = model or os.environ.get("SVA_GEN_MODEL", "claude-opus-4-7")
        self.max_retries = max_retries

    def generate(self, rtl_code: str) -> GenerationResult:
        messages = build_messages(rtl_code)

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                )
                raw_text = response.content[0].text
                return self._parse_response(raw_text)
            except (APIError, json.JSONDecodeError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    sleep_s = 2 ** attempt
                    time.sleep(sleep_s)
                    continue
                raise RuntimeError(
                    f"Failed after {self.max_retries} attempts. Last error: {e}"
                ) from e

        raise RuntimeError(f"Unreachable, but last error was: {last_error}")

    @staticmethod
    def _parse_response(raw: str) -> GenerationResult:
        # Strip any accidental markdown fences
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        data = json.loads(text)

        props = [
            Property(
                name=p["name"],
                description=p["description"],
                kind=p["kind"],
                sva_code=p["sva_code"],
                justification=p["justification"],
            )
            for p in data.get("properties", [])
        ]

        return GenerationResult(
            module_name=data["module_name"],
            summary=data["summary"],
            clock_signal=data["clock_signal"],
            reset_signal=data["reset_signal"],
            properties=props,
            notes=data.get("notes", ""),
            raw_response=raw,
        )