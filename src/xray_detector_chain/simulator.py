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

def offset_map(level, row_offsets, col_offsets, pixel_sigma, rng):
    """Stage 6 (fixed pattern): offset of every binned pixel (ADU), the same in every frame.

    level: mean offset (ADU); row_offsets (rows,), col_offsets (cols,): ADU;
    pixel_sigma: std of the per-pixel offset (ADU), drawn once from rng.
    """
    pixel = rng.normal(0, pixel_sigma, size=(row_offsets.size, col_offsets.size))
    return level + row_offsets[:, np.newaxis] + col_offsets[np.newaxis, :] + pixel

def read_noise(shape, sigma, rng):
    """Stage 7: Gaussian read noise (ADU), drawn again for every frame."""
    return rng.normal(0, sigma, size=shape)


def digitize(adu, full_scale):
    """Stage 8: round to integer ADU, clip to [0, full_scale], store as uint16 like the TIFF files."""
    return np.clip(np.round(adu), 0, full_scale).astype(np.uint16)