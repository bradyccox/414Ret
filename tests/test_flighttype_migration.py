"""Legacy FlightType migration.

The 414th's retired SCRAMBLE QRA flight type (and the older ISR type) must map
onto their live equivalents so campaigns saved on older builds still load. Both
the runtime ``_missing_`` path and the unpickler path are covered.
"""

from __future__ import annotations

import io

from game.ato.flighttype import FlightType
from game.persistency import MigrationUnpickler


def test_scramble_is_gone_from_the_enum() -> None:
    assert not any(member.value == "Scramble" for member in FlightType)


def test_missing_maps_legacy_values() -> None:
    # Enum value lookup (the path pickle uses to rehydrate an enum member).
    assert FlightType("Scramble") is FlightType.BARCAP
    assert FlightType("ISR") is FlightType.JAMMING
    # Live values are unaffected.
    assert FlightType("BARCAP") is FlightType.BARCAP


def test_unpickler_flight_type_migration() -> None:
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    migrate = unpickler._handle_flight_type("game.ato.flighttype", "FlightType")
    assert migrate is not None
    assert migrate("Scramble") is FlightType.BARCAP
    assert migrate("ISR") is FlightType.JAMMING
    assert migrate("TARCAP") is FlightType.TARCAP


def test_unpickler_ignores_non_flight_type() -> None:
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    assert unpickler._handle_flight_type("game.ato.flighttype", "Squadron") is None
    assert unpickler._handle_flight_type("some.other.module", "FlightType") is None
