# X-ray detector chain: calibration, filtering and image quality

Processing chain for a 14-bit flat-panel X-ray detector, from raw ADU values to corrected projections with measured image quality. Each correction and metric is validated on a simulated detector with known parameters before being applied to real data.

**Status:** Milestone 1 (data exploration) complete. Work in progress.

## Data

Real data: Walnut dataset (Der Sarkissian et al., *Scientific Data*, 2019, [arXiv:1905.04787](https://arxiv.org/abs/1905.04787)), licence CC BY 4.0. This project uses Walnut 1, orbit `tubeV1` (high source position).

- **Detector**: Dexela 1512NDT, 14-bit (full scale 16383 ADU), stored as uint16 TIFF. Hardware 2×2 binning: each pixel is the mean of 4 physical pixels. Effective pixel size 149.6 µm.
- **Units**: values are ADU (analog-to-digital units), not photon counts.
- **Files per orbit**: one dark (`di000000.tif`), two flats acquired before and after the scan (`io000000.tif`, `io000001.tif`), 1201 projections. No frame averaging.
- **Acquisition**: 40 kV, 12 W, 80 ms exposure.

### Findings

Details and plots in [`notebooks/01_exploration.ipynb`](notebooks/01_exploration.ipynb). Rows and columns refer to the array as stored in the TIFF files.

**Format and range**
- Arrays are 768 × 972 (rows × columns), transposed with respect to the figures in the paper.
- Flat maximum 14394 ADU = 88% of full scale: no saturation, ~2000 ADU headroom.

**Dark (offset)**
- Range 304–417 ADU, mean 343.
- Each row has its own offset: row means jump by tens of ADU from row to row (std 10.5 ADU), accounting for 88% of the dark variance. This appears as horizontal stripes (vertical in the paper).
- Across columns: slow variation of ~14 ADU, lower in the centre; even columns ~2 ADU higher than odd ones; the first ~20 columns are up to ~4 ADU higher.
- Residual per-pixel variability ≈ 2.4 ADU. With a single dark, per-pixel offset and temporal read noise cannot be separated.
- The walnut outline is visible in the dark although the source was off: residual image from the previous exposure (detector lag).

**Flat drift during the orbit**
- Mean of (F1 − D)/(F0 − D) = 1.0064: the flat increased by 0.64% between start and end of the orbit.
- The change is not uniform: its 31×31 local mean ranges from 1.0035 behind the walnut silhouette to 1.0101 outside it. An object-shaped change points to detector memory of the scan (lag), the same effect visible in the dark.
- Consequence: no single flat represents the whole scan. Flat-field correction carries an object-dependent residual error of order 0.5%.

**Noise: variance vs mean**
- Method: var(F1 − F0)/2 in 16×16 blocks against the block mean of the dark-subtracted flats. The difference removes everything fixed (beam profile, pixel gain, dark), leaving only noise.
- Variance grows with signal, from ~45 ADU² at 7000 ADU to ~90 ADU² at 13500 ADU, consistent with counting statistics.
- Linear fit: slope 0.0073 ADU per quantum (effective gain), intercept −10.9 ADU². The negative intercept is unphysical: data cover only 6000–14000 ADU, so extrapolation to zero is unreliable. Scatter between blocks is larger than expected from 256 pixels per block (~9%).
- The slope is an effective gain, not ADU per X-ray photon: scintillator blur and 2×2 binning reduce the measured variance. To be quantified with the simulator.

## Out of scope

- Correction of the residual image (lag): observed and quantified, not corrected.
- Offset drift between orbits.
- DQE (only if time allows).

## Roadmap

- [x] 1. Data exploration
- [ ] 2. Detector simulator with known ground truth
- [ ] 3. Calibration: offset/gain correction, conversion gain, defective pixels
- [ ] 4. Filtering: noise/sharpness trade-off measured with NPS and MTF
- [ ] 5. Image quality: SNR, CNR, NPS, slanted-edge MTF against an analytic reference
- [ ] 6. MATLAB reference implementation, verified by Python tests in CI
- [ ] 7. DICOM export, report, release v1.0

## Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml`, `uv.lock`).

```bash
uv sync                  # creates .venv and installs the locked dependencies
uv run jupyter lab       # opens the notebooks
```

Data are not included in the repository. Download `Walnut1.zip` from Zenodo (DOI [10.5281/zenodo.2686725](https://doi.org/10.5281/zenodo.2686725)), extract `Walnut1/Projections/tubeV1/`, and set `DATA` in the first notebook cell to that folder.

## References

- Der Sarkissian H., Lucka F., van Eijnatten M., Colacicco G., Coban S. B., Batenburg K. J. *A cone-beam X-ray CT data collection designed for machine learning*. Scientific Data, 2019. [arXiv:1905.04787](https://arxiv.org/abs/1905.04787)
