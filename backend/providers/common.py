import random
import re

VALID_CHOICES = ("kamen", "nuzky", "papir")

_ALIAS_TO_CHOICE = {
    "kamen": "kamen",
    "rock": "kamen",
    "stone": "kamen",
    "boulder": "kamen",
    "🪨": "kamen",
    "nuzky": "nuzky",
    "scissors": "nuzky",
    "scissor": "nuzky",
    "shears": "nuzky",
    "✂": "nuzky",
    "✂️": "nuzky",
    "papir": "papir",
    "paper": "papir",
    "sheet": "papir",
    "📄": "papir",
}


def random_choice() -> str:
    return random.choice(VALID_CHOICES)


def normalize_choice(raw: str) -> str | None:
    if not raw:
        return None

    text = raw.strip().lower()
    if text in VALID_CHOICES:
        return text

    tokens = re.findall(r"[a-z]+|[🪨📄✂]", text)
    for token in tokens:
        if token in _ALIAS_TO_CHOICE:
            return _ALIAS_TO_CHOICE[token]

    for alias, choice in _ALIAS_TO_CHOICE.items():
        if alias in text:
            return choice

    return None


def build_prompt(history: str) -> str:
    return (
        "You are choosing a move in a rock-paper-scissors elimination tournament. "
        "Use the provided session history as strategic context. "
        "Reply with exactly one lowercase word: kamen, nuzky, or papir.\n\n"
        "Session history:\n"
        f"{history}"
    )
