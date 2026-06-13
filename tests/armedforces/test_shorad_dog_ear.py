from game.armedforces.forcegroup import ForceGroup


def _unit_names(group: ForceGroup) -> set[str]:
    return {unit.variant_id for unit in group.units}


def test_soviet_style_shorad_presets_include_dog_ear() -> None:
    assert "Dog Ear radar" in _unit_names(ForceGroup.from_preset_group("SA-9 SHORAD"))
    assert "Dog Ear radar" in _unit_names(ForceGroup.from_preset_group("SA-15 SHORAD"))
    assert "Dog Ear radar" in _unit_names(ForceGroup.from_preset_group("SA-19 SHORAD"))


def test_non_soviet_shorad_presets_do_not_include_dog_ear() -> None:
    assert "Dog Ear radar" not in _unit_names(ForceGroup.from_preset_group("Roland"))
