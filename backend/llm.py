import os
import json
from google import genai
from google.genai import types


def _make_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)


def _model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class GeminiClient:
    """
    Thin wrapper around the Gemini API with two call modes:

    assistant_call — multi-turn chat for the coding assistant.
    judge_call     — single-turn structured prompt for the LLM judge
                     that writes session narratives.
    """

    def __init__(self):
        self._client = _make_client()
        self._model = _model_name()

    def assistant_call(self, prompt: str, history: list[dict], system_prompt: str) -> str:
        """
        Send a message to the coding assistant and return the response text.

        history: list of {"role": "user"|"model", "content": str} dicts
                 representing the conversation so far (excluding the new prompt).
        """
        gemini_history = [
            types.Content(
                role=msg["role"],
                parts=[types.Part(text=msg["content"])],
            )
            for msg in history
        ]

        chat = self._client.chats.create(
            model=self._model,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            history=gemini_history,
        )
        response = chat.send_message(prompt)
        return response.text

    def judge_call(self, user_prompt: str, system_prompt: str) -> str:
        """
        Ask the LLM judge to produce a narrative summary given a formatted prompt.

        user_prompt:   The substituted template containing scores and excerpts
        system_prompt: System instructions defining the rubric
        """

        response = self._client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
        return response.text
