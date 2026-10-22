"""Simulator stages checked against answers known in advance."""

import numpy as np
import pytest

from xray_detector_chain import load_params
from xray_detector_chain.simulator import (
    apply_gain,
    bin_mean,
    blur,
    digitize,
    mean_quanta,
    offset_map,
    quantum_noise,
    read_noise,
    to_physical,
)


def test_bin_mean_by_hand():
    x = np.array([[1, 2, 5, 6],
                  [3, 4, 7, 8],
                  [0, 0, 1, 1],
                  [0, 4, 1, 1]], dtype=float)
    # blocks: (1 + 2 + 3 + 4) / 4 = 2.5, (5 + 6 + 7 + 8) / 4 = 6.5, (0 + 0 + 0 + 4) / 4 = 1, (1 + 1 + 1 + 1) / 4 = 1
    assert np.array_equal(bin_mean(x), [[2.5, 6.5], [1.0, 1.0]])


def test_to_physical_then_bin_returns_input():
    # README: a binned map copied into 2 x 2 blocks and binned again is returned unchanged
    rng = np.random.default_rng(1)
    x = rng.normal(size=(6, 8))  # small random "binned map"
    up = to_physical(x)
    assert up.shape == (12, 16)
    assert np.all(up[0:2, 0:2] == x[0, 0])  # the first 2 x 2 block holds the first value
    assert np.allclose(bin_mean(up), x)  # equal up to float rounding (sum of 4 values / 4)


def test_mean_quanta_by_hand():
    beam = np.full((2, 3), 11000.0)  # binned grid, ADU
    # 11000 ADU / 0.110 ADU per quantum = 100000 quanta per physical pixel; second flat x 1.0064 = 100640
    q0 = mean_quanta(beam, g=0.110)
    q1 = mean_quanta(beam, g=0.110, drift=1.0064)
    assert q0.shape == (4, 6)  # physical grid
    assert q0 == pytest.approx(np.full((4, 6), 100000.0))
    assert q1 == pytest.approx(np.full((4, 6), 100640.0))


def test_quantum_noise_is_poisson():
    rng = np.random.default_rng(0)
    mean = np.full((500, 500), 1000.0)  # 250 000 pixels, 1000 quanta each
    counts = quantum_noise(mean, rng)
    # Poisson: mean 1000 and variance 1000, so var/mean = 1
    # tolerance: the variance from N values has relative error sqrt(2/N) = 0.0028; 0.015 is ~5 times that
    assert counts.mean() == pytest.approx(1000, rel=0.001)
    assert counts.var() / counts.mean() == pytest.approx(1, rel=0.015)
    # independent pixels: correlation with the right neighbour ~0 (error 1/sqrt(N) = 0.002)
    c = np.corrcoef(counts[:, :-1].ravel(), counts[:, 1:].ravel())[0, 1]
    assert abs(c) < 0.01

def test_blur_keeps_mean_and_spreads_noise():
    rng = np.random.default_rng(2)
    counts = quantum_noise(np.full((600, 600), 1000.0), rng)  # white noise: var = mean = 1000
    sigma = 1.08  # physical pixels
    out = blur(counts, sigma)
    # 1. the blur moves quanta, it does not create or destroy them: same mean
    assert out.mean() == pytest.approx(counts.mean(), rel=1e-6)
    # 2. variance kept by a Gaussian PSF: 1 / (4 pi sigma^2) = 0.0682 at sigma = 1.08
    #    tolerance: this ratio varies by 0.7 % between seeds (correlated pixels); 0.04 is ~6 times that
    assert out.var() / counts.var() == pytest.approx(1 / (4 * np.pi * sigma**2), rel=0.04)
    # 3. neighbours become correlated: exp(-1 / (4 sigma^2)) = 0.807 at sigma = 1.08
    x = out - out.mean()
    rho1 = np.mean(x[:, :-1] * x[:, 1:]) / x.var()
    assert rho1 == pytest.approx(np.exp(-1 / (4 * sigma**2)), abs=0.01)

def test_gain_by_hand():
    quanta = np.full((4, 6), 100000.0)  # physical grid
    gain_rel = np.zeros((2, 3))  # binned grid
    gain_rel[0, 0] = 0.01  # first binned pixel +1 %
    adu = apply_gain(quanta, g=0.110, gain_rel=gain_rel)
    # 100000 x 0.110 = 11000 ADU; the first 2 x 2 physical block x 1.01 = 11110 ADU
    assert adu.shape == (4, 6)
    assert adu[0:2, 0:2] == pytest.approx(np.full((2, 2), 11110.0))
    assert adu[2:, :] == pytest.approx(np.full((2, 6), 11000.0))


def test_noiseless_chain_reproduces_flat():
    # README: beam x (1 + gain map) reproduces the measured flat. Without noise and blur,
    # stages 1, 4 and 5 must return it: g cancels (divided at stage 1, multiplied at stage 4)
    rng = np.random.default_rng(3)
    beam = rng.uniform(7000, 14000, size=(6, 8))  # binned grid, ADU
    gain_rel = rng.normal(0, 0.005, size=(6, 8))  # 0.5 % pattern, binned grid
    flat = bin_mean(apply_gain(mean_quanta(beam, g=0.110), g=0.110, gain_rel=gain_rel))
    assert flat == pytest.approx(beam * (1 + gain_rel), rel=1e-12)

def slope(x):
    """var/mean of an image (ADU): the variance-mean slope of a uniform flat."""
    return x.var() / x.mean()


def test_slope_of_the_chain():
    # README, "Blur and binning lower the variance-mean slope": g, then g/4, then g/4 x R_blur
    g, sigma_blur, r_blur = 0.110, 1.08, 0.222  # R_blur: notebook 02 lookup table (rho_1 = 0.50)
    beam = np.full((300, 300), 11000.0)  # binned grid, ADU -> 100000 quanta per physical pixel
    no_pattern = np.zeros((300, 300))  # gain map off: only noise is left
    counts = quantum_noise(mean_quanta(beam, g), np.random.default_rng(4))
    # tolerances: ~5 times the spread of each slope over 20 seeds (0.2 %, 0.4 %, 0.6 %);
    # the last one also covers +0.7 %: R_blur is 0.2234 at sigma 1.08, 0.222 at the unrounded 1.085
    physical = apply_gain(counts, g, no_pattern)  # no blur, no binning
    assert slope(physical) == pytest.approx(g, rel=0.01)
    assert slope(bin_mean(physical)) == pytest.approx(g / 4, rel=0.025)  # binning only
    blurred = bin_mean(apply_gain(blur(counts, sigma_blur), g, no_pattern))  # blur and binning
    assert slope(blurred) == pytest.approx(g / 4 * r_blur, rel=0.035)  # 0.0061: the k_eff target

def test_offset_map_by_hand():
    rows = np.array([0.0, 10.0])  # 2 row offsets, ADU
    cols = np.array([0.0, 1.0, 2.0])  # 3 column offsets, ADU
    m = offset_map(300.0, rows, cols, pixel_sigma=0.0, rng=np.random.default_rng(0))
    # pixel (r, c) = 300 + rows[r] + cols[c]
    assert np.array_equal(m, [[300.0, 301.0, 302.0], [310.0, 311.0, 312.0]])


def test_offset_map_with_measured_parameters():
    scalars, maps = load_params()
    true = scalars["true"]
    m = offset_map(true["offset_level"]["value"], maps["row_offsets"], maps["col_offsets"],
                   true["offset_pixel_sigma"]["value"], np.random.default_rng(0))
    assert m.shape == (768, 972)
    # per-pixel part: what is left after removing level, rows and columns has std 1.20 ADU
    # tolerance: std from 746 496 values, relative error 1/sqrt(2N) = 0.0008; 0.005 is ~6 times that
    pixel = m - true["offset_level"]["value"] - maps["row_offsets"][:, None] - maps["col_offsets"][None, :]
    assert pixel.std() == pytest.approx(1.20, rel=0.005)
    # row stripes: std of the jumps between row means = 12.34 ADU (target of the simulated dark)
    # the per-pixel part adds 1.20 x sqrt(2 / 972) = 0.05 ADU in quadrature: negligible
    jumps = np.diff(m.mean(axis=1))
    target = scalars["targets"]["row_jump_std_dark"]["value"]
    assert jumps.std() == pytest.approx(target, rel=0.01)

def test_two_darks_give_measured_read_noise():
    scalars, maps = load_params()
    true = scalars["true"]
    rng = np.random.default_rng(5)
    offsets = offset_map(true["offset_level"]["value"], maps["row_offsets"], maps["col_offsets"],
                         true["offset_pixel_sigma"]["value"], rng)  # stage 6: drawn once
    darks = [digitize(offsets + read_noise(offsets.shape, true["read_noise"]["value"], rng),
                      true["full_scale"]["value"]) for _ in range(2)]  # stages 7 and 8: every frame
    diff = darks[0].astype(np.float64) - darks[1]  # float first: uint16 0 - 1 would give 65535
    # same method as the real darks: std(D1 - D2) / sqrt(2) = 0.542 ADU (0.459 read + 0.289 rounding)
    # tolerance: 0.06 % spread over 20 seeds; 0.005 is ~8 times that
    target = scalars["targets"]["sigma_read_measured"]["value"]
    assert diff.std() / np.sqrt(2) == pytest.approx(target, rel=0.005)