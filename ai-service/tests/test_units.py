import pytest

from app.ingestion.units import (UnknownUnitError, annualise, canonical_token,
                                 convert, quantity_kind)


def test_canonical_tokens():
    assert canonical_token("kWh (Net CV)") == "kWh"
    assert canonical_token("litres") == "litre"
    assert canonical_token("tonne.km") == "tonne_km"
    assert canonical_token("Cubic Metres") == "m3"
    assert canonical_token("MT") == "tonne"


def test_energy_conversions():
    assert convert(480000, "kWh", "MWh").canonical_value == pytest.approx(480.0)
    assert convert(1, "GJ", "kWh").canonical_value == pytest.approx(277.7778, rel=1e-4)
    assert convert(1, "mmBtu", "kWh").canonical_value == pytest.approx(293.071, rel=1e-4)


def test_mass_and_volume():
    assert convert(2.5, "tonnes", "kg").canonical_value == pytest.approx(2500.0)
    assert convert(1, "m3", "litre").canonical_value == pytest.approx(1000.0)
    assert convert(1, "gallon", "litre").canonical_value == pytest.approx(3.78541, rel=1e-5)


def test_cross_quantity_conversion_is_refused():
    with pytest.raises(UnknownUnitError, match="different"):
        convert(1, "litre", "kg")


def test_unknown_unit_is_never_guessed():
    with pytest.raises(UnknownUnitError):
        canonical_token("cylinders")


def test_annualisation_is_explicit():
    v, note = annualise(1000, "month")
    assert v == 12000
    assert "12" in note
    with pytest.raises(UnknownUnitError):
        annualise(1, "shift")


def test_quantity_kinds():
    assert quantity_kind("kWh") == "energy"
    assert quantity_kind("tonnes") == "mass"
    assert quantity_kind("litres") == "volume"
