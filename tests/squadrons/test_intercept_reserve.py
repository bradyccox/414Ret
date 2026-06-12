from __future__ import annotations

from game.squadrons.intercept_reserve import (
    clamp_intercept_reserve,
    qra_resource_count,
    repropagated_intercept_reserve,
    seeded_intercept_reserve,
)


def test_non_barcap_squadron_is_unchanged() -> None:
    assert seeded_intercept_reserve(False, 0, 4, 12) == 0


def test_explicit_non_zero_reserve_is_preserved() -> None:
    assert seeded_intercept_reserve(True, 3, 4, 12) == 3


def test_barcap_squadron_seeded_from_default() -> None:
    assert seeded_intercept_reserve(True, 0, 4, 12) == 4


def test_seed_is_clamped_to_max_size() -> None:
    assert seeded_intercept_reserve(True, 0, 10, 4) == 4


def test_zero_default_leaves_reserve_at_zero() -> None:
    assert seeded_intercept_reserve(True, 0, 0, 12) == 0


def test_clamp_within_bounds_is_unchanged() -> None:
    assert clamp_intercept_reserve(3, 12) == 3


def test_clamp_caps_at_max_size() -> None:
    assert clamp_intercept_reserve(99, 12) == 12


def test_clamp_floors_at_zero() -> None:
    assert clamp_intercept_reserve(-5, 12) == 0


def test_clamp_with_zero_max_size_returns_zero() -> None:
    # An empty squadron (max_size 0) can hold no reserve, even from a YAML default.
    assert clamp_intercept_reserve(5, 0) == 0


def test_resource_count_is_reserve_when_owned_is_sufficient() -> None:
    assert qra_resource_count(4, 10) == 4


def test_resource_count_capped_at_owned_after_attrition() -> None:
    # Squadron attrited below its reserve must not field more jets than it owns.
    assert qra_resource_count(5, 3) == 3


def test_resource_count_is_zero_when_nothing_owned() -> None:
    assert qra_resource_count(4, 0) == 0


def test_resource_count_capped_by_available_pilots() -> None:
    assert qra_resource_count(4, 10, available_pilots=2) == 2


def test_resource_count_airframes_win_when_fewer_than_pilots() -> None:
    assert qra_resource_count(4, 1, available_pilots=10) == 1


def test_resource_count_no_pilot_cap_when_pilots_none() -> None:
    assert qra_resource_count(4, 10, available_pilots=None) == 4


def test_resource_count_zero_with_no_available_pilots() -> None:
    assert qra_resource_count(4, 10, available_pilots=0) == 0


def test_repropagate_non_barcap_squadron_is_unchanged() -> None:
    # A non-BARCAP squadron never carries QRA, even if its value equals the default.
    assert repropagated_intercept_reserve(False, 0, 0, 4, 12) == 0


def test_repropagate_tracking_squadron_moves_to_new_default() -> None:
    # Opt-in on an existing campaign: 0 -> 4 bumps a squadron still at the old default.
    assert repropagated_intercept_reserve(True, 0, 0, 4, 12) == 4


def test_repropagate_user_set_value_is_left_alone() -> None:
    # Reserve 3 != clamped old default 0, so the user's choice is preserved.
    assert repropagated_intercept_reserve(True, 3, 0, 4, 12) == 3


def test_repropagate_matches_clamped_old_default() -> None:
    # max_size 4 clamped the old default 6 down to 4 at seed time; that squadron
    # still tracks the default and follows it down to the new (clamped) value.
    assert repropagated_intercept_reserve(True, 4, 6, 2, 4) == 2


def test_repropagate_new_value_is_clamped_to_max_size() -> None:
    assert repropagated_intercept_reserve(True, 0, 0, 10, 4) == 4


def test_repropagate_no_op_when_old_equals_new() -> None:
    assert repropagated_intercept_reserve(True, 2, 2, 2, 12) == 2
