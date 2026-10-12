# X-ray detector chain: calibration, filtering and image quality

Processing chain for a 14-bit flat-panel X-ray detector, from raw ADU values to corrected projections with measured image quality. Each correction and metric is validated on a simulated detector with known parameters before being applied to real data.

**Status:** Milestone 1 (data exploration) complete. Milestone 2 in progress: model defined, parameters measured on real data ([`notebooks/02_simulator_parameters.ipynb`](notebooks/02_simulator_parameters.ipynb)), implementation next.

## Data

Real data: Walnut dataset (Der Sarkissian et al., *Scientific Data*, 2019, [arXiv:1905.04787](https://arxiv.org/abs/1905.04787)), licence CC BY 4.0. This project uses Walnut 1, orbit `tubeV1` (high source position). The darks of orbits `tubeV2` and `tubeV3` are used only to separate read noise from per-pixel offset.

- **Detector**: Dexela 1512NDT, 14-bit (full scale 16383 ADU), stored as uint16 TIFF. Hardware 2×2 binning: each pixel is the mean of 4 physical pixels. Effective pixel size 149.6 µm.
- **Units**: values are ADU (analog-to-digital units), not photon counts.
- **Files per orbit**: one dark (`di000000.tif`), two flats acquired before and after the scan (`io000000.tif`, `io000001.tif`), 1201 projections. No frame averaging.
- **Acquisition**: 40 kV, 12 W, 80 ms exposure.

### Findings

Details and plots in [`notebooks/01_exploration.ipynb`](notebooks/01_exploration.ipynb) and [`notebooks/02_simulator_parameters.ipynb`](notebooks/02_simulator_parameters.ipynb). Rows and columns refer to the array as stored in the TIFF files and displayed with `imshow`.

**Format and range**
- Arrays are 768 × 972 (rows × columns), transposed with respect to the figures in the paper.
- Flat maximum 14394 ADU = 88% of full scale: no saturation, ~2000 ADU headroom.

**Dark (offset)**
- Range 304–417 ADU, mean 343, standard deviation 11.1 ADU.
- Each row has its own offset: row means jump by tens of ADU from row to row (std 10.5 ADU), accounting for 88% of the dark variance. This appears as horizontal stripes (vertical in the paper). The stripes are fixed from frame to frame and identical in the darks of different orbits (correlation 1.000).
- Across columns: even columns ~2 ADU higher than odd ones; the first ~20 columns are up to ~4 ADU higher; a slow variation of ~14 ADU, lower in the centre, which follows the residual image of the walnut.
- After removing row and column offsets, the per-pixel spread is 2.5 ADU, mostly residual image: removing also the slow component leaves 1.32 ADU (see Measured parameters).
- The walnut outline is visible in the dark although the source was off: residual image from the previous exposure (detector lag).
- The offset level changes between orbits: 342.7, 359.4, 364.9 ADU for tubeV1, tubeV2, tubeV3.

**Flat (dark-subtracted)**
- The non-uniformity is dominated by the beam profile: along the central row the signal rises smoothly from ~7500 to ~13900 ADU, with its maximum near column 800, not at the centre of the image.
- On top of it, a fixed hexagonal pattern: ~10 px between cell centres vertically and ~8.7 px between staggered columns horizontally (ratio √3/2 of a regular honeycomb), i.e. cells of ~1.5 mm. Std of the relative pattern 0.53 % in a bright 100 × 100 region; quantum noise contributes ~0.05 %.
- Thin horizontal lines, some isolated roughly every 128 rows (≈ 64, 192, 320, 448, 576, 704), probably readout-block boundaries. They have the same amplitude in % where the beam is weak and strong, so they are a gain effect, not an offset.
- The first and last ~20 rows of the relative pattern drop by up to 2.6 %: detector edge or smoothing artefact, to check.

**Flat drift during the orbit**
- Mean of (F1 − D)/(F0 − D) = 1.0064: the flat increased by 0.64% between start and end of the orbit.
- The change is not uniform: its 31×31 local mean ranges from 1.0035 behind the walnut silhouette to 1.0101 outside it. An object-shaped change points to detector memory of the scan (lag), the same effect visible in the dark.
- Consequence: no single flat represents the whole scan. Flat-field correction carries an object-dependent residual error of order 0.5%.

**Noise: variance vs mean**
- Method: var(F1 − F0)/2 in 16×16 blocks against the block mean of the dark-subtracted flats. The difference removes everything fixed (beam profile, pixel gain, dark), leaving only noise.
- Variance grows with signal, from ~45 ADU² at 7000 ADU to ~90 ADU² at 13500 ADU, consistent with counting statistics.
- Linear fit: slope 0.0073 ADU per quantum (effective gain), intercept −10.9 ADU². The negative intercept is unphysical: data cover only 6000–14000 ADU, so extrapolation to zero is unreliable. Scatter between blocks is larger than expected from 256 pixels per block (~9%).
- The slope is an effective gain, not ADU per X-ray photon: scintillator blur and 2×2 binning reduce the measured variance (see below).

## Simulator (Milestone 2)

Real data have no ground truth: a measured gain or MTF cannot be checked against a known answer. The simulator generates darks, flats and test images from parameters chosen or measured in advance, so that every correction and metric can be validated against the true value before it is applied to the walnut data.

### Signal chain

Stages in order. The physical grid is 1536 × 1944 pixels (74.8 µm); the binned grid is 768 × 972 (149.6 µm), as stored in the TIFF files. Units up to stage 3 are X-ray quanta.

| # | Stage | Grid | Input → output | Noise added | True parameters |
|---|---|---|---|---|---|
| 1 | Beam | physical | — → mean quanta per pixel (float) | none | mean quanta map (smooth shape × level) |
| 2 | Quantum noise | physical | mean quanta → counted quanta (integer) | Poisson: variance = mean, independent between pixels | random seed |
| 3 | Scintillator blur | physical | counted quanta → blurred quanta (float) | none: the existing noise is spread to neighbours, which become correlated | Gaussian σ (physical pixels) |
| 4 | Gain, incl. defective pixels | physical | quanta → ADU (float) | none (fixed pattern) | global gain g (ADU per quantum); relative gain map (measured, hexagonal pattern and row lines); defect mask |
| 5 | 2×2 binning (mean) | physical → binned | ADU → ADU | none: lowers the noise per pixel | — |
| 6 | Offset | binned | ADU → ADU | none (fixed pattern) | mean level; row offsets; even/odd column offset; edge offset of the first ~20 columns; per-pixel offset map |
| 7 | Read noise | binned | ADU → ADU | Gaussian, new in every frame | σ_read (electronic part) |
| 8 | Rounding and saturation | binned | ADU (float) → uint16 | quantisation, σ = 1/√12 ≈ 0.29 ADU (included in the measured σ_read) | full scale 16383 |

### Parameter sources

- **Measured on real data**: offset level; row offsets (fast row-to-row component of the dark row means, without the slow part due to the residual image); even/odd column offset (~2 ADU); edge offset (~4 ADU, first ~20 columns); σ_read and per-pixel offset (from the darks of three orbits); relative gain map (flat − dark divided by its smoothed version); beam shape (smooth part of flat − dark).
- **Chosen**: blur σ; random seed; number, type and position of defective pixels.
- **Derived**: g, chosen together with σ so that the simulated variance–mean slope matches the measured 0.0073; beam level, from the smooth flat − dark divided by g.
- **Fixed**: binning factor 2; full scale 16383.

### Measured parameters

Details in [`notebooks/02_simulator_parameters.ipynb`](notebooks/02_simulator_parameters.ipynb).

| Parameter | Value | Stage | Method |
|---|---|---|---|
| Offset level | 342.7 ADU (tubeV1) | 6 | mean of the dark |
| Row offsets | 768 measured values; std 8.7 ADU, row-to-row jumps 12.34 ADU | 6 | dark row means minus their Gaussian-smoothed version (20 rows). Rows are independent: jumps/√2 = 8.73 ADU, corrected std 8.66 ADU |
| Per-pixel offset | σ = 1.20 ADU | 6 | one dark with rows, columns and slow part removed; read noise subtracted in quadrature |
| Read noise, measured | 0.54 ADU, includes rounding | — | std(D1 − D2)/√2 over three orbit pairs (0.538–0.547); smoothing σ = 3 px, its noise loss corrected |
| Read noise, electronic | 0.46 ADU = √(0.54² − 1/12) | 7 | rounding (0.29 ADU) is added at stage 8 |
| Relative gain map | measured map, anomalous pixels replaced, replicated in 2×2 blocks | 4 | (mean flat − dark) divided by its Gaussian-smoothed version (σ = 15 px) |

### Findings that shaped the model

Checks in [`notebooks/01_exploration.ipynb`](notebooks/01_exploration.ipynb), section "Checks for the simulator model", and in [`notebooks/02_simulator_parameters.ipynb`](notebooks/02_simulator_parameters.ipynb).

- **Row offsets are fixed.** Row-to-row jumps of the row means have std 12.3 ADU in the dark and 0.55 ADU in F1 − F0. The difference of two frames cancels everything fixed: stripes that changed between frames would survive in it. Pixel noise alone would give jumps of ~0.4 ADU (approximate estimate). Row offsets therefore belong to the fixed offset (stage 6), not to the noise.
- **Per-pixel offset and read noise are separated with three darks.** The difference of two darks cancels the fixed offset: var(D1 − D2) = 2 σ_read². Row, column and slow components (the residual image differs in each orbit) are removed first. The 2.5 ADU spread found in Milestone 1 was mostly residual image.
- **Blur and binning lower the variance–mean slope by at least a factor 4.** Without blur or binning the slope equals g. The mean of 4 independent pixels has one quarter of the variance and the same mean, so binning alone gives g/4. Blur lowers the variance further without changing the mean, so the measured slope is at most g/4: in this model the true gain is g ≥ 4 × 0.0073 ≈ 0.03 ADU per quantum.
- **A dead physical pixel reads 75% of its neighbours after binning, not zero.** Defect detection must look for deviations from the neighbours, not for zero values.
- **The flat non-uniformity is mostly beam profile.** The slow variation (~6000 ADU across a row) is assigned to the beam, the fast pixel-to-pixel part to the gain map.
- **The measured gain map is used directly.** Replicating each binned value in a 2×2 block on the physical grid returns exactly the measured map after binning. A synthetic honeycomb was not used: flat-field correction removes any multiplicative pattern, so the choice cannot change the calibration results.

### Simplifications and exclusions

- **Conversion noise ignored.** The number of light photons produced by each X-ray in the scintillator varies; this extra noise is not modelled, and units stay X-ray quanta through stage 3.
- **Offset and read noise on the binned grid.** Physically they act on each physical pixel before binning. Adding them after binning, with the values measured on the binned data, reproduces the measured statistics without having to infer unmeasurable physical-pixel values.
- **Slow gain variation attributed to the beam.** Flats alone cannot separate the two; both are removed by flat-field correction.
- **Gain map known only on the binned grid.** The four physical pixels of a 2×2 block share the same gain; after binning this is indistinguishable from the real detector.
- **Gaussian blur.** A single parameter σ, with an analytic MTF for the slanted-edge validation.
- **Single quantisation step at the end.** Whether hardware binning happens before or after digitisation is unknown. Rounding adds 0.29 ADU, not negligible against the 0.54 ADU read noise, so it is subtracted in quadrature from the measured σ_read.
- **Not simulated**: residual image (lag), including the slow column variation of the dark that follows it; offset drift between orbits.

### Open decisions before implementation

- Flat drift between start and end of the orbit: simulate its uniform part (+0.64%) as a single factor between the two flats.
- Placement of hot pixels (physical or binned grid).
- Replacement of anomalous pixels in the measured gain map.
- Low values in the first and last ~20 rows of the gain map: detector edge or smoothing artefact.
- Format of the ground-truth file read by the tests.

### Validation (planned)

- Variance–mean slope on simulated flats: g without blur and binning, g/4 with binning only, below g/4 with both.
- Simulated darks: σ_read from the difference of two darks ≈ 0.54 ADU; std of row-to-row jumps ≈ 12.34 ADU; per-pixel offset ≈ 1.20 ADU.

## Out of scope

- Correction of the residual image (lag): observed and quantified, not corrected or simulated.
- Offset drift between orbits (measured: up to 22 ADU), not simulated or corrected.
- DQE (only if time allows).

## Roadmap

- [x] 1. Data exploration
- [ ] 2. Detector simulator with known ground truth (model defined, parameters measured, implementation next)
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

Data are not included in the repository. Download `Walnut1.zip` from Zenodo (DOI [10.5281/zenodo.2686725](https://doi.org/10.5281/zenodo.2686725)) and extract `Walnut1/Projections/tubeV1/`, plus the darks `tubeV2/di000000.tif` and `tubeV3/di000000.tif` into sibling folders of `tubeV1`. Set `DATA` in the first code cell of each notebook to the `tubeV1` folder.

## References

- Der Sarkissian H., Lucka F., van Eijnatten M., Colacicco G., Coban S. B., Batenburg K. J. *A cone-beam X-ray CT data collection designed for machine learning*. Scientific Data, 2019. [arXiv:1905.04787](https://arxiv.org/abs/1905.04787)