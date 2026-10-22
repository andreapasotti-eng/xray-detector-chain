import numpy as np
from scipy.ndimage import gaussian_filter

BIN = 2  


def to_physical(x):
    """Binned grid (768, 972) -> physical grid (1536, 1944): each value copied into a 2 x 2 block."""
    return np.repeat(np.repeat(x, BIN, axis=0), BIN, axis=1)


def bin_mean(x):
    """Physical grid -> binned grid: mean of each 2 x 2 block (stage 5)."""
    rows, cols = x.shape
    return x.reshape(rows // BIN, BIN, cols // BIN, BIN).mean(axis=(1, 3))  # mean over a and b: inside each block

def mean_quanta(beam, g, drift=1.0):
    """Stage 1: beam (binned grid, ADU) -> mean quanta per physical pixel (physical grid, float)."""
    return to_physical(beam) * drift / g


def quantum_noise(mean, rng):
    """Stage 2: mean quanta -> counted quanta (integer). Poisson: variance = mean, independent pixels."""
    return rng.poisson(mean)

def blur(counts, sigma):
    """Stage 3: counted quanta -> blurred quanta (float). Gaussian PSF, sigma in physical pixels."""
    return gaussian_filter(counts.astype(np.float64), sigma)

def apply_gain(quanta, g, gain_rel):
    """Stage 4: blurred quanta (physical grid) -> ADU (float). gain_rel: binned grid, fraction."""
    return quanta * g * (1 + to_physical(gain_rel))