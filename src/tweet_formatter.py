"""Generate tweet text for live match events."""
from __future__ import annotations


def start(player: str, club: str, opponent: str, competition: str, watch: dict) -> str:
    return (
        f"{player} starts for {club} vs {opponent} in the {competition}. "
        f"Watch: {watch['name']} ({watch['link']})"
    )


def sub_in(player: str, club: str, minute: int) -> str:
    return f"{player} is on for {club} at the {minute}' mark. #USMNT"


def sub_out(player: str, club: str, minute: int) -> str:
    return f"{player} comes off for {club} in the {minute}' minute. #USMNT"


def goal(player: str, club: str, opponent: str, minute: int, score: str, competition: str) -> str:
    return (
        f"GOAL! {player} scores for {club} vs {opponent} "
        f"in the {competition} at {minute}' — {score}. #USMNT"
    )


def assist(player: str, club: str, opponent: str, minute: int, score: str, competition: str) -> str:
    return (
        f"ASSIST! {player} sets one up for {club} vs {opponent} "
        f"in the {competition} at {minute}' — {score}. #USMNT"
    )


def full_time(club: str, opponent: str, score: str, result: str, competition: str) -> str:
    return f"FT: {club} {score} {opponent} ({result}) in the {competition}. #USMNT"
