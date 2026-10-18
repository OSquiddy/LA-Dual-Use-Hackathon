"""Separate caller evidence from the agent's questions without rewriting stored transcripts."""
import re


def caller_text(transcript: str) -> str:
    turns = list(re.finditer(r"(?im)^(agent|assistant|user|caller|resident):[ \t]*", transcript))
    if not turns:
        return transcript  # Seed/plain resident statements have no speaker labels.
    return "\n".join(
        transcript[turn.end():turns[n + 1].start() if n + 1 < len(turns) else len(transcript)]
        for n, turn in enumerate(turns)
        if turn.group(1).lower() in {"user", "caller", "resident"}
    )
