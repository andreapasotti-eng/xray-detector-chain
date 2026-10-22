"""The parameter files are complete, have the right shapes and agree with each other."""

import numpy as np
import pytest
from scipy.ndimage import median_filter

from xray_detector_chain import load_params

SCALARS, MAPS = load_params()  # read once, used by every test below
ROWS, COLS = SCALARS["meta"]["binned_shape"]  # 768, 972


def test_shapes():
    assert (ROWS, COLS) == (768, 972)
    assert SCALARS["meta"]["physical_shape"] == [2 * ROWS, 2 * COLS]  # 2 x 2 binning
    assert MAPS["row_offsets"].shape == (ROWS,)
    assert MAPS["col_offsets"].shape == (COLS,)
    assert MAPS["gain_rel"].shape == (ROWS, COLS)
    assert MAPS["beam"].shape == (ROWS, COLS)


def test_every_entry_is_complete():
    for section in ["true", "targets"]:
        for key, entry in SCALARS[section].items():
            assert set(entry) == {"value", "unit", "stage", "source"}, f"{section}/{key}"


def test_stages():
    # inputs act at a stage of the chain (1-8); targets are measured on the output, no stage
    assert all(1 <= e["stage"] <= 8 for e in SCALARS["true"].values())
    assert all(e["stage"] is None for e in SCALARS["targets"].values())


def test_units():
    true = SCALARS["true"]
    assert true["g"]["unit"] == "ADU per quantum, physical pixel"
    assert true["sigma_blur"]["unit"] == "physical pixels"
    assert true["read_noise"]["unit"] == "ADU"
    assert SCALARS["targets"]["k_eff_median"]["unit"] == "ADU per quantum, binned"


def test_read_noise_plus_rounding_gives_measured():
    # identity, not a physical check: 0.459 was computed from 0.542 as sqrt(0.542^2 - 1/12)
    # tolerance: 0.459 is rounded to 3 decimals, which moves the result by up to 0.08 %
    sigma_el = SCALARS["true"]["read_noise"]["value"]
    measured = SCALARS["targets"]["sigma_read_measured"]["value"]
    assert np.sqrt(sigma_el**2 + 1 / 12) == pytest.approx(measured, rel=0.002)


def test_gain_map_matches_its_target():
    # identity: npz and json come from the same notebook run (same crop, same robust spread)
    box = MAPS["gain_rel"][334:434, 750:850]  # bright 100 x 100 crop of notebook 02, section 1c
    p16, p84 = np.percentile(box, [16, 84])
    target = SCALARS["targets"]["gain_map_std"]["value"]  # 0.0047, rounded to 4 decimals
    assert (p84 - p16) / 2 == pytest.approx(target, abs=0.00006)


def test_gain_map_is_clean():
    # notebook 02, section 1e: 630 pixels (0.084 %) had score > 2 % before the replacement.
    # rel_clean must have almost none; with the original rel this test fails.
    g = MAPS["gain_rel"].astype(np.float64)
    res_row = g - median_filter(g, size=(1, 5))  # along the row
    res_col = g - median_filter(g, size=(5, 1))  # along the column
    score = np.minimum(np.abs(res_row), np.abs(res_col))
    assert (score > 0.02).mean() < 0.0001  # less than 0.01 % (75 pixels)


def test_beam_is_positive():
    # stage 1 turns the beam into mean quanta per pixel (beam / g): it must be > 0 everywhere
    assert MAPS["beam"].min() > 0
