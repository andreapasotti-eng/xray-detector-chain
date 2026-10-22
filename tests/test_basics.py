import numpy as np
import pytest


def test_binning_is_mean_of_block():
    # one 2 x 2 block of physical pixels: (1 + 2 + 3 + 4) / 4 = 2.5
    block = np.array([[1.0, 2.0], [3.0, 4.0]])
    assert block.mean() == 2.5


def test_rounding_noise():
    # rounding to the nearest integer adds an error with std 1/sqrt(12) = 0.2887 ADU (sigma_q)
    rng = np.random.default_rng(0)
    x = rng.uniform(0, 1000, 1_000_000)  # 1 million values, ADU
    err = np.round(x) - x  # rounding error, between -0.5 and +0.5
    # tolerance: the std from 10^6 values has relative error ~0.0005; 0.002 is ~4 times that
    assert err.std() == pytest.approx(1 / np.sqrt(12), rel=0.002)