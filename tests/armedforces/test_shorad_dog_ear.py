import pytest

from game import persistency
from game.armedforces.forcegroup import ForceGroup


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # ForceGroup/layout preset loading reads from the DCS saved-game folder,
    # which is only configured once the app boots. Point it at an empty temp
    # dir so loading falls back to the bundled resources/ presets.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


_DOG_EAR = 'MCC-SR Sborka "Dog Ear" SR'


def _unit_names(group: ForceGroup) -> set[str]:
    return {unit.variant_id for unit in group.units}


def test_soviet_style_shorad_presets_include_dog_ear() -> None:
    assert _DOG_EAR in _unit_names(ForceGroup.from_preset_group("SA-9 SHORAD"))
    assert _DOG_EAR in _unit_names(ForceGroup.from_preset_group("SA-15 SHORAD"))
    assert _DOG_EAR in _unit_names(ForceGroup.from_preset_group("SA-19 SHORAD"))


def test_non_soviet_shorad_presets_do_not_include_dog_ear() -> None:
    assert _DOG_EAR not in _unit_names(ForceGroup.from_preset_group("Roland"))


def test_big_soviet_sam_sites_include_dog_ear_point_defense() -> None:
    # SA-2/3/5 batteries and S-300 sites carry a Dog Ear search radar in their
    # point-defense, so the Sborka shows up across the IADS, not just at SHORAD.
    for preset in ("SA-2/S-75", "SA-3/S-125", "SA-5/S-200", "SA-10/S-300PS"):
        assert _DOG_EAR in _unit_names(ForceGroup.from_preset_group(preset)), preset
