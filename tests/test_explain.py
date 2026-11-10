import pytest

from dnb.coach.explain import (
    MAX_EXPLANATIONS,
    GeminiProvider,
    MockProvider,
    build_prompt,
    default_provider,
    describe_edge,
    explain_mistakes,
    matches_facts,
    template_explanation,
)
from dnb.coach.review import MoveReview


@pytest.fixture(autouse=True)
def no_real_llm(monkeypatch):
    """Tests never call a real LLM, even on a machine with a key set."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


class Canned:
    def __init__(self, text: str = "Try to keep your boxes safe.") -> None:
        self.text = text
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.text


class Broken:
    def complete(self, prompt: str) -> str:
        raise TimeoutError("no response")


def mistake(**overrides) -> MoveReview:
    fields = {
        "ply": 4,
        "move": 0,  # horizontal, dot row 1, dot columns 1-2
        "best_move": 12,  # vertical, dot column 1, dot rows 1-2
        "score": -0.5,
        "best_score": 0.5,
        "label": "mistake",
        "rows": 3,
        "cols": 3,
        "boxes_taken": 0,
        "boxes_given_away": 2,
        "left_three_sided": True,
    }
    return MoveReview(**(fields | overrides))


def test_describe_edge_counts_dots_from_the_top_left():
    assert describe_edge(3, 3, 0) == (
        "the horizontal line in dot row 1, between dot columns 1 and 2"
    )
    assert describe_edge(3, 3, 12) == "the vertical line in dot column 1, between dot rows 1 and 2"


def test_prompt_states_the_reviewed_facts():
    prompt = build_prompt(mistake(boxes_taken=1, boxes_given_away=2, left_three_sided=False))
    assert describe_edge(3, 3, 0) in prompt
    assert describe_edge(3, 3, 12) in prompt
    assert "completed with this move: 1" in prompt
    assert "claimed on their next turn: 2" in prompt
    assert "ended the turn: no" in prompt


def test_only_the_biggest_mistakes_are_explained():
    reviews = [
        mistake(ply=0, score=0.0, best_score=0.3),
        mistake(ply=2, score=-1.0, best_score=1.0),
        mistake(ply=4, score=-0.5, best_score=0.5),
        mistake(ply=6, score=-0.2, best_score=0.5),
        mistake(ply=8, label="okay", score=-1.0, best_score=1.0),
    ]
    provider = Canned()
    explanations = explain_mistakes(reviews, provider)
    assert set(explanations) == {2, 4, 6}
    assert len(provider.prompts) == MAX_EXPLANATIONS


def test_no_mistakes_means_no_llm_call():
    provider = Canned()
    assert explain_mistakes([mistake(label="good")], provider) == {}
    assert provider.prompts == []


def test_a_truthful_explanation_is_used():
    text = "That line gave your opponent two boxes."
    assert explain_mistakes([mistake()], Canned(text)) == {4: text}


def test_a_failing_provider_falls_back_to_the_template():
    assert explain_mistakes([mistake()], Broken()) == {4: template_explanation(mistake())}


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "That move cost you seven boxes.",  # the opponent claimed 2
        "You gave away 7 boxes.",
        "Edge 19 was much better.",
    ],
)
def test_explanations_that_contradict_the_review_are_replaced(text):
    assert explain_mistakes([mistake()], Canned(text)) == {4: template_explanation(mistake())}


def test_three_sided_claim_needs_a_three_sided_box():
    facts = mistake(left_three_sided=False)
    assert not matches_facts("This left a three-sided box.", facts)
    assert not matches_facts("This left a box with 3 sides.", facts)
    assert matches_facts("This left a three-sided box.", mistake())


def test_free_box_claim_needs_a_box_given_away():
    assert not matches_facts("You gave a free box.", mistake(boxes_given_away=0))
    assert matches_facts("You gave a free box.", mistake())


def test_a_better_one_is_not_read_as_a_number():
    assert matches_facts("A better one was nearby.", mistake(boxes_given_away=0))


def test_mock_text_is_only_shown_when_it_is_true():
    true_case = mistake()
    assert explain_mistakes([true_case], MockProvider()) == {4: MockProvider().complete("")}
    false_case = mistake(left_three_sided=False, boxes_given_away=0)
    assert explain_mistakes([false_case], MockProvider()) == {4: template_explanation(false_case)}


def test_template_only_states_what_happened():
    assert template_explanation(mistake(boxes_given_away=1)) == (
        "This move left a box with three sides. "
        "Your opponent claimed 1 box on their next turn. "
        f"A better move was {describe_edge(3, 3, 12)}."
    )
    assert template_explanation(mistake(left_three_sided=False, boxes_given_away=0)) == (
        f"A better move was {describe_edge(3, 3, 12)}."
    )


def test_template_always_passes_the_fact_check():
    for facts in (mistake(), mistake(left_three_sided=False, boxes_given_away=0)):
        assert matches_facts(template_explanation(facts), facts)


def test_default_provider_is_the_mock_without_a_key():
    assert isinstance(default_provider(), MockProvider)


def test_gemini_client_builds_with_a_timeout():
    # Builds the client only; nothing is sent.
    assert GeminiProvider(api_key="not-a-real-key").client is not None
