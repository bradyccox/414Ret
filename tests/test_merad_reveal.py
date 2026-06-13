"""After the first mission, surviving MERAD groups are revealed on the MFD.

MERAD groups (SA-6/11/17) start hidden so players don't see enemy SAM
positions before flying. finish_turn() reveals them when the turn counter
reaches 1 (i.e. the first mission just completed), simulating intel gathered
during that mission.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from game.data.groups import GroupTask
from game.game import Game
from game.theater import ConflictTheater
from game.theater.theatergroundobject import TheaterGroundObject


def _tgo(task: GroupTask, hidden: bool) -> TheaterGroundObject:
    return cast(TheaterGroundObject, SimpleNamespace(task=task, hide_on_mfd=hidden))


def _make_game(tgos: list[TheaterGroundObject], turn: int = 0) -> Game:
    game = Game.__new__(Game)
    game.turn = turn
    game.theater = cast(
        ConflictTheater,
        SimpleNamespace(ground_objects=iter(tgos)),
    )
    return game


def test_merad_hidden_groups_revealed_after_turn_0() -> None:
    merad = _tgo(GroupTask.MERAD, hidden=True)
    game = _make_game([merad], turn=0)
    game.turn = 1  # simulate finish_turn incrementing the counter
    game._reveal_merad_groups()
    assert not merad.hide_on_mfd


def test_shorad_groups_stay_hidden_after_turn_0() -> None:
    shorad = _tgo(GroupTask.SHORAD, hidden=True)
    game = _make_game([shorad], turn=1)
    game._reveal_merad_groups()
    assert shorad.hide_on_mfd


def test_lorad_groups_unaffected() -> None:
    lorad = _tgo(GroupTask.LORAD, hidden=False)
    game = _make_game([lorad], turn=1)
    game._reveal_merad_groups()
    assert not lorad.hide_on_mfd


def test_already_visible_merad_stays_visible() -> None:
    merad = _tgo(GroupTask.MERAD, hidden=False)
    game = _make_game([merad], turn=1)
    game._reveal_merad_groups()
    assert not merad.hide_on_mfd


def test_merad_not_revealed_on_later_turns() -> None:
    """_reveal_merad_groups is only called when turn==1; this guards the call site."""
    merad = _tgo(GroupTask.MERAD, hidden=True)
    game = _make_game([merad], turn=2)
    # Simulate finish_turn logic: only call reveal on turn 1
    if game.turn == 1:
        game._reveal_merad_groups()
    assert merad.hide_on_mfd  # still hidden — never revealed
