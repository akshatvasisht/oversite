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

    def judge_call(self, scores: dict, excerpts: str, system_prompt: str) -> str:
        """
        Ask the LLM judge to produce a narrative summary given scoring outputs
        and representative excerpts from the session.

        scores:   dict of component scores (e.g. structural_scores, prompt_quality_scores)
        excerpts: relevant text pulled from the session (prompts, diffs, etc.)
        """
        preamble = """\
CONTEXT
-------
MadData is an AI-assisted coding interview platform. Candidates solve algorithmic
problems inside a custom IDE that includes an AI coding assistant (Gemini). The
platform records every action taken during the session and scores candidates across
three dimensions:

  Component 1 — Structural Behavior
    Captures how the candidate organized their problem-solving process: time spent
    reading vs. coding vs. testing, how often they ran the code, whether they wrote
    tests, how deeply they iterated (edit → run → fix cycles), and how much they
    explored the problem (file opens, panel switches) before writing a line.

  Component 2 — Prompt Quality
    Evaluates the quality of the candidate's AI interactions: were prompts specific
    and well-scoped, or vague and repeated? Did prompts demonstrate understanding of
    the problem? Did the candidate ask follow-up questions or blindly accept the first
    response?

  Component 3 — Critical Review
    Measures how critically the candidate engaged with AI suggestions: did they paste
    verbatim, make cosmetic edits, or substantially rework the output? Candidates who
    rejected or heavily modified suggestions score higher on this dimension.

OVERALL LABELS
--------------
  over_reliant  (weighted_score < 2.5): Candidate leaned heavily on AI output with
    little independent thought — low iteration, passive acceptance, weak prompts.

  balanced      (2.5 ≤ weighted_score ≤ 3.5): Candidate used AI as a tool while
    maintaining problem-solving agency — reasonable iteration, some critical review.

  strategic     (weighted_score > 3.5): Candidate used AI strategically — strong
    independent exploration, high-quality prompts, meaningful modification of
    AI suggestions.

SCORE SCALE
-----------
All component sub-scores are on a 1–5 scale. weighted_score is a weighted average
of the three components. Higher is better.

---
"""
        prompt = (
            f"{preamble}"
            f"SESSION SCORES\n--------------\n{json.dumps(scores, indent=2)}\n\n"
            f"SESSION EXCERPTS\n----------------\n{excerpts}"
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
        return response.text
