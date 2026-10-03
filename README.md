# xray-detector-chain

Processing chain for a flat-panel X-ray detector, from raw 16-bit counts to calibrated projections and
quantitative image-quality metrics.

**Status:** work in progress.

## Scope
- Simulated detector with known ground truth (offset, gain, defective pixels, noise, blur)
- Offset/gain calibration and defective-pixel correction, validated on the simulation
- 16-bit filtering with measured effect on noise and sharpness
- Image quality: SNR, CNR, noise power spectrum, MTF (slanted edge)
- Application to real cone-beam projections from the CWI Walnut dataset

## Data
Real data: *Cone-Beam X-Ray CT Data Collection Designed for Machine Learning*,
Der Sarkissian et al., Scientific Data (2019), CC BY 4.0. Data are not included in this repository.

## Development
    uv sync
    uv run pytest
