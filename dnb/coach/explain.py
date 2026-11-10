"""LLM explanations of the 2-3 biggest mistakes.

Providers are pluggable. Tests and CI always use MockProvider, so nobody needs an API key
to run them. Set GEMINI_API_KEY (see .env.example) to use Gemini for real.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Protocol

from dnb.coach.review import MoveReview
from dnb.engine import edge_coords

logger = logging.getLogger(__name__)

MAX_EXPLANATIONS = 3
REQUEST_TIMEOUT_MS = 15_000

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
# "one" only counts next to "box": "a better one" is not a claim about a number.
_NUMBERS = re.compile(r"\b\d+\b|\bone(?= box)|\b(?:two|three|four|five|six|seven|eight|nine|ten)\b")
_THREE_SIDES = re.compile(r"\b(?:three|3)[ -]sided?s?\b")


class LLMProvider(Protocol):
    def complete(self, prompt: str) -> str: ...


class MockProvider:
    def complete(self, prompt: str) -> str:
        return "This move left a box with three sides, so your opponent got a free box."


class GeminiProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        from google import genai  # optional dependency: `uv sync --extra llm`

        self.client = genai.Client(
            api_key=api_key or os.environ["GEMINI_API_KEY"],
            http_options={"timeout": REQUEST_TIMEOUT_MS},
        )
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    def complete(self, prompt: str) -> str:
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return response.text or ""


def default_provider() -> LLMProvider:
    if not os.environ.get("GEMINI_API_KEY"):
        return MockProvider()
    try:
        return GeminiProvider()
    except ImportError:
        logger.warning("GEMINI_API_KEY is set but google-genai is not installed; using the mock")
        return MockProvider()


def describe_edge(rows: int, cols: int, edge: int) -> str:
    """Edge index -> words a player can find on the board, counting dots from the top left."""
    kind, r, c = edge_coords(rows, cols, edge)
    if kind == "h":
        return f"the horizontal line in dot row {r + 1}, between dot columns {c + 1} and {c + 2}"
    return f"the vertical line in dot column {c + 1}, between dot rows {r + 1} and {r + 2}"


def build_prompt(mistake: MoveReview) -> str:
    played = describe_edge(mistake.rows, mistake.cols, mistake.move)
    better = describe_edge(mistake.rows, mistake.cols, mistake.best_move)
    three_sided = "yes" if mistake.left_three_sided else "no"
    return (
        "You are a friendly Dots and Boxes coach. In one or two plain sentences, tell the player "
        "why this move was a mistake.\n"
        "Use only the facts below. Do not add any other moves, numbers or reasons, and do not "
        "predict what would have happened.\n\n"
        f"- The player drew {played}.\n"
        f"- A better move was {better}.\n"
        f"- Boxes the player completed with this move: {mistake.boxes_taken}.\n"
        f"- This move left a box with three sides and ended the turn: {three_sided}.\n"
        f"- Boxes the opponent claimed on their next turn: {mistake.boxes_given_away}.\n"
    )


def template_explanation(mistake: MoveReview) -> str:
    """Always true, so it stands in whenever the LLM fails or contradicts the facts."""
    sentences = []
    if mistake.left_three_sided:
        sentences.append("This move left a box with three sides.")
    if mistake.boxes_given_away:
        boxes = "box" if mistake.boxes_given_away == 1 else "boxes"
        sentences.append(
            f"Your opponent claimed {mistake.boxes_given_away} {boxes} on their next turn."
        )
    better = describe_edge(mistake.rows, mistake.cols, mistake.best_move)
    sentences.append(f"A better move was {better}.")
    return " ".join(sentences)


def matches_facts(text: str, mistake: MoveReview) -> bool:
    """Reject explanations that are empty, or state numbers or claims the review doesn't support."""
    lowered = text.lower()
    if not lowered.strip():
        return False
    if _THREE_SIDES.search(lowered) and not mistake.left_three_sided:
        return False
    if "free box" in lowered and not mistake.boxes_given_away:
        return False
    allowed = {mistake.boxes_taken, mistake.boxes_given_away}
    allowed.update(int(n) for n in _NUMBERS.findall(build_prompt(mistake)) if n.isdigit())
    if mistake.left_three_sided:
        allowed.add(3)
    stated = (int(n) if n.isdigit() else _NUMBER_WORDS[n] for n in _NUMBERS.findall(lowered))
    return all(n in allowed for n in stated)


def _explain_one(mistake: MoveReview, provider: LLMProvider) -> str:
    try:
        text = provider.complete(build_prompt(mistake)).strip()
    except Exception:
        logger.exception("LLM call failed; using the template explanation")
        return template_explanation(mistake)
    if matches_facts(text, mistake):
        return text
    logger.warning("LLM explanation contradicted the review; using the template: %r", text)
    return template_explanation(mistake)


def explain_mistakes(
    reviews: list[MoveReview], provider: LLMProvider | None = None
) -> dict[int, str]:
    """Explanations of the biggest mistakes, keyed by ply so the UI can match them to moves."""
    mistakes = [r for r in reviews if r.label == "mistake"]
    if not mistakes:
        return {}
    provider = provider or default_provider()
    biggest = sorted(mistakes, key=lambda r: r.gap, reverse=True)[:MAX_EXPLANATIONS]
    return {m.ply: _explain_one(m, provider) for m in biggest}
