# X-ray detector chain: calibration, filtering and image quality

Processing chain for a 14-bit flat-panel X-ray detector, from raw ADU values to corrected projections with measured image quality. Each correction and metric is validated on a simulated detector with known parameters before being applied to real data.

**Status:** Milestone 1 (data exploration) complete. Milestone 2 in progress: parameters measured on real data ([`notebooks/02_simulator_parameters.ipynb`](notebooks/02_simulator_parameters.ipynb)), ground-truth file in [`params/`](params/), simulator stages 1–8 implemented in [`src/xray_detector_chain/`](src/xray_detector_chain/) and tested stage by stage; validation of complete simulated darks and flats against the measured targets next.

## Data

Real data: Walnut dataset (Der Sarkissian et al., *Scientific Data*, 2019, [arXiv:1905.04787](https://arxiv.org/abs/1905.04787)), licence CC BY 4.0. This project uses Walnut 1, orbit `tubeV1` (high source position). The darks of orbits `tubeV2` and `tubeV3` are used only to separate read noise from per-pixel offset and to check that the fixed offsets are the same in every orbit.

- **Detector**: Dexela 1512NDT, 14-bit (full scale 16383 ADU), stored as uint16 TIFF. Hardware 2×2 binning, treated as the mean of 4 physical pixels (see Assumptions). Effective pixel size 149.6 µm.
- **Units**: values are ADU (analog-to-digital units), not photon counts.
- **Files per orbit**: one dark (`di000000.tif`), two flats acquired before and after the scan (`io000000.tif`, `io000001.tif`), 1201 projections. No frame averaging.
- **Acquisition**: 40 kV, 12 W, 80 ms exposure.

### Findings

Details and plots in [`notebooks/01_exploration.ipynb`](notebooks/01_exploration.ipynb) and [`notebooks/02_simulator_parameters.ipynb`](notebooks/02_simulator_parameters.ipynb). Rows and columns refer to the array as stored in the TIFF files and displayed with `imshow`.

**Format and range**
- Arrays are 768 × 972 (rows × columns), transposed with respect to the figures in the paper.
- Flat maximum 14394 ADU (flat acquired after the scan) = 88% of full scale: no ADC clipping, ~2000 ADU headroom.

**Dark (offset)**
- Range 304–417 ADU, mean 343, standard deviation 11.1 ADU.
- Each row has its own offset: row means jump by tens of ADU from row to row (std 10.5 ADU), accounting for 88% of the dark variance. This appears as horizontal stripes (vertical in the paper). The stripes are fixed from frame to frame and have the same shape and amplitude in the darks of the three orbits (correlation 0.9996, slope 0.996–0.997).
- Across columns: even columns 2.23 ADU higher than odd ones; the first ~20 columns are up to ~4–5 ADU higher; a slow variation of ~14 ADU, lower in the centre, which follows the residual image of the walnut and differs between orbits.
- After removing row and column offsets, the per-pixel spread is 2.5 ADU, mostly residual image: removing also the slow component leaves 1.32 ADU (see Measured parameters).
- The walnut outline is visible in the dark although the source was off: residual image from the previous exposure (detector lag).
- The offset level changes between orbits: 342.7, 359.4, 364.9 ADU for tubeV1, tubeV2, tubeV3.

**Flat (dark-subtracted)**
- The non-uniformity is dominated by the beam profile: along the central row the signal rises smoothly from ~7500 to ~13900 ADU, with its maximum near column 800, not at the centre of the image.
- On top of it, a fixed hexagonal pattern: ~10 px between cell centres vertically and ~8.7 px between staggered columns horizontally (ratio √3/2 of a regular honeycomb), i.e. cells of ~1.5 mm. Std of the relative pattern 0.53 % in a bright 100 × 100 region (robust spread 0.47 %); quantum noise contributes ~0.05 %.
- Thin horizontal lines, some isolated roughly every 128 rows (≈ 64, 192, 320, 448, 576, 704), probably readout-block boundaries. They have the same amplitude in % where the beam is weak and strong, so they are a gain effect, not an offset.
- 630 point defects (0.084 %), almost all dark, deviate by more than 2 % from their neighbours along both the row and the column (−4.5 % on average). Their mean neighbourhood is a one-pixel cross, not a line: isolated defects, not hexagon walls. The cross is consistent with a defect blurred by the scintillator.
- The first and last ~20 rows of the relative pattern drop by up to 2.6 %: smoothing artefact, not a detector edge. The drop grows with the smoothing width (2 / 15 / 27 rows below −0.5 % for σ = 5 / 15 / 30 px) and the raw row profile shows no drop.

**Flat drift during the orbit**
- Mean of (F1 − D)/(F0 − D) = 1.0064: the flat increased by 0.64% between start and end of the orbit.
- The change is not uniform: its 31×31 local mean ranges from 1.0035 behind the walnut silhouette to 1.0101 outside it. An object-shaped change points to detector memory of the scan (lag), the same effect visible in the dark.
- Consequence: no single flat represents the whole scan. The residual image seen in the second flat is not the one present in each projection, which the flats cannot measure; 1.0035 behind the walnut is an upper bound of the drift not caused by the residual image.

**Noise: variance vs mean**
- Method: in 16×16 blocks, var(d) / (2k) against the block mean of the two dark-subtracted flats, with d = F1 − k·F0 and k the 31×31 local ratio F1/F0. The difference removes everything fixed (beam profile, pixel gain, dark) and the smooth drift; dividing by 2k instead of 2 accounts for the scaled noise of F0.
- Median var/mean over all blocks: **0.0061 ADU per quantum** (effective slope, binned pixels). Mean 0.0064.
- var/mean depends on the position on the detector, not on the signal: at the same signal (11268 ADU ± 5 %) it is 0.00706 in the top half and 0.00534 in the bottom half (+32 %, uncertainty ~2 %); left and right differ by 8 %.
- The earlier linear fit (slope 0.0073, intercept −10.9 ADU², unphysical) mixed this position dependence with the signal. The drift edges are not the cause: the drift step across one block is at most ~16 ADU and the correlation of the block residuals with it is 0.22.
- Correlation between neighbouring pixels: rho_1 = 0.47 in the top half, 0.53 in the bottom half, equal horizontally and vertically. With a Gaussian scintillator PSF this is σ = 1.03 and 1.14 physical pixels: the blur difference explains a factor 1.17 of the 1.32 top/bottom ratio; the remaining factor 1.13 comes from the effective gain (gain or spectrum), not separable with flats.
- Spread between blocks: 18.5 % (robust), larger than the ~9 % expected for 256 independent pixels; it includes the position dependence and the pixel correlation.
- The slope is an effective gain, not ADU per X-ray photon: scintillator blur and 2×2 binning reduce the measured variance (see below).

## Simulator (Milestone 2)

Real data have no ground truth: a measured gain or MTF cannot be checked against a known answer. The simulator generates darks, flats and test images from parameters chosen or measured in advance, so that every correction and metric can be validated against the true value before it is applied to the walnut data.

### Signal chain

Stages in order. The physical grid is 1536 × 1944 pixels (74.8 µm); the binned grid is 768 × 972 (149.6 µm), as stored in the TIFF files. Units up to stage 3 are X-ray quanta.

| # | Stage | Grid | Input → output | Noise added | True parameters |
|---|---|---|---|---|---|
| 1 | Beam | physical | — → mean quanta per pixel (float) | none | beam map (smooth flat − dark) / g; second flat × 1.0064 |
| 2 | Quantum noise | physical | mean quanta → counted quanta (integer) | Poisson: variance = mean, independent between pixels | random seed |
| 3 | Scintillator blur | physical | counted quanta → blurred quanta (float) | none: the existing noise is spread to neighbours, which become correlated | Gaussian σ = 1.08 physical pixels |
| 4 | Gain, incl. defective pixels | physical | quanta → ADU (float) | none (fixed pattern) | g = 0.110 ADU per quantum; relative gain map (measured, hexagonal pattern and row lines); dead and low-gain pixels |
| 5 | 2×2 binning (mean) | physical → binned | ADU → ADU | none: lowers the noise per pixel | — |
| 6 | Offset | binned | ADU → ADU | none (fixed pattern) | mean level; row offsets (768 values); column offsets (972 values: even/odd, edge); per-pixel offset map; hot pixels |
| 7 | Read noise | binned | ADU → ADU | Gaussian, new in every frame | σ_read = 0.459 ADU (electronic part) |
| 8 | Rounding and saturation | binned | ADU (float) → uint16 | quantisation, σ = 1/√12 ≈ 0.289 ADU (included in the measured σ_read) | full scale 16383 |

### Parameter sources

- **Measured on real data**: offset level; row offsets; column offsets; σ_read and per-pixel offset (from the darks of three orbits); relative gain map (flat − dark divided by its smoothed version); beam shape (smooth part of flat − dark); scintillator blur σ (neighbour correlation, Gaussian PSF); effective gain g (variance–mean slope and blur, assuming mean binning); uniform flat drift.
- **Chosen**: random seed; number, type and position of defective pixels.
- **Derived**: beam level in quanta = smooth flat − dark divided by g.
- **Fixed**: binning factor 2; full scale 16383.

### Ground-truth file

[`params/walnut_tubeV1.json`](params/walnut_tubeV1.json) holds the scalar parameters, each with value, unit, stage and source, in two sections:
- `true`: the inputs the simulator is built from (for example read noise 0.459 ADU);
- `targets`: what the analysis of the real data measured (for example σ_read 0.542 ADU). Simulated data, analysed with the same functions, must reproduce the targets; comparing with `true` would only check that the simulator returns its own inputs.

[`params/walnut_tubeV1_maps.npz`](params/walnut_tubeV1_maps.npz) holds the measured vectors and maps: `row_offsets` (768), `col_offsets` (972), `gain_rel` (768 × 972, anomalous pixels replaced, see below), `beam` (768 × 972, ADU). They are derived from the Walnut data (CC BY 4.0, cited above) and stored in the repository so that tests run without the dataset.

### Measured parameters

Details in [`notebooks/02_simulator_parameters.ipynb`](notebooks/02_simulator_parameters.ipynb).

| Parameter | Value | Stage | Method |
|---|---|---|---|
| Offset level | 342.7 ADU (tubeV1) | 6 | mean of the dark |
| Row offsets | 768 measured values; std 8.7 ADU, row-to-row jumps 12.34 ADU | 6 | dark row means minus their Gaussian-smoothed version (20 rows). Rows are independent: jumps/√2 = 8.73 ADU, corrected std 8.66 ADU. Same shape and amplitude in three orbits (slope 0.996–0.997) |
| Column offsets | 972 measured values; even/odd 2.23 ADU | 6 | column means (row offsets removed) minus their Gaussian-smoothed version (20 columns). The slow tail of the edge offset (first ~20–40 columns) is underestimated: a wider filter lets the residual image in (correlation between orbits 0.96 at 50 columns, 0.89 at 100) |
| Per-pixel offset | σ = 1.20 ADU | 6 | one dark with rows, columns and slow part removed; read noise subtracted in quadrature |
| Read noise, measured | 0.542 ADU, includes rounding | — | std(D1 − D2)/√2 over three orbit pairs (0.538–0.547); smoothing σ = 3 px, its noise loss corrected |
| Read noise, electronic | 0.459 ADU = √(0.542² − 1/12) | 7 | rounding (0.289 ADU) is added at stage 8 |
| Relative gain map | measured map, replicated in 2×2 blocks; 630 point defects replaced | 4 | (mean flat − dark) divided by its Gaussian-smoothed version (σ = 15 px). Beam and gain map come from the same smoothing, so beam × (1 + gain map) reproduces the measured flat exactly, edge rows included. Pixels deviating by more than 2 % from the 5-pixel medians along the row and along the column replaced with the median along the row (row lines kept) |
| Scintillator blur | σ = 1.08 physical pixels (1.03 top half, 1.14 bottom half) | 3 | neighbour correlation rho_1 of d (0.50) converted with a lookup table from simulated white noise (Gaussian blur on the physical grid, 2×2 mean binning); 1.085 before rounding |
| Effective gain | g = 0.110 ADU per quantum (0.104 bottom, 0.118 top) | 4 | g = 4 × k_eff / R_blur, with k_eff = 0.0061 and R_blur = 0.222 the variance reduction by the blur at σ = 1.08. Assumes mean binning: with sum binning g would be 4 times smaller |
| Flat drift | 1.0064, uniform | 1 | mean of (F1 − D)/(F0 − D); the object-shaped part is residual image, not simulated |

### Findings that shaped the model

Checks in [`notebooks/01_exploration.ipynb`](notebooks/01_exploration.ipynb), section "Checks for the simulator model", and in [`notebooks/02_simulator_parameters.ipynb`](notebooks/02_simulator_parameters.ipynb).

- **Row offsets are fixed.** Row-to-row jumps of the row means have std 12.34 ADU in the dark and 0.55 ADU in F1 − F0. The difference of two frames cancels everything fixed: stripes that changed between frames would survive in it. The jumps expected from the noise alone are 0.532 ADU on d, from σ² / N × S0 × (1 − c), where S0 is the sum of the pixel correlations along a row and c the correlation between adjacent row means; measured 0.531 ADU. The extra 0.14 ADU in F1 − F0 is the slope of the smooth drift. A temporal row noise would add to the measured jumps: it is below 0.08 ADU (2σ), so it is not simulated.
- **Per-pixel offset and read noise are separated with three darks.** The difference of two darks cancels the fixed offset: var(D1 − D2) = 2 σ_read². Row, column and slow components (the residual image differs in each orbit) are removed first. The 2.5 ADU spread found in Milestone 1 was mostly residual image.
- **Blur and binning lower the variance–mean slope.** Without blur or binning the slope equals g. The mean of 4 independent pixels has one quarter of the variance and the same mean, so binning alone gives g/4. Blur lowers the variance further without changing the mean, by the factor R_blur = 0.222 at σ = 1.08: k_eff = g/4 × R_blur.
- **A dead physical pixel reads 75% of its neighbours after binning, not zero.** Defect detection must look for deviations from the neighbours, not for zero values.
- **The flat non-uniformity is mostly beam profile.** The slow variation (~6000 ADU across a row) is assigned to the beam, the fast pixel-to-pixel part to the gain map. The noise supports this choice only partly: var/mean does not follow the signal, but it changes across the detector (see Simplifications).
- **Anomalous pixels of the gain map are replaced with a threshold in % of gain, not in σ.** The spread of the residual after a 5-pixel median (0.256 %) is the hexagonal pattern itself, five times the quantum noise: a 5σ threshold flagged 0.56 % of the pixels (0.19 % requiring both directions), cutting into the hexagon walls. The threshold (2 %) lies above the walls and well below the defects simulated in Milestone 3 (−12.5 % to −25 % after binning), which real outliers would otherwise turn into false positives. After the replacement the robust spread of the pattern is unchanged (0.467 → 0.466 %); weaker anomalies (1–2 %) remain.
- **The measured gain map is used directly.** Replicating each binned value in a 2×2 block on the physical grid returns exactly the measured map after binning. A synthetic honeycomb was not used: flat-field correction removes any multiplicative pattern, so the choice cannot change the calibration results.

### Simplifications and exclusions

- **One gain and one blur for the whole detector.** On the real detector var/mean at equal signal is 32 % higher in the top half than in the bottom half: about half of it (in log scale) is a wider blur in the bottom half, the rest a different effective gain. The simulator uses the field averages (g = 0.110, σ = 1.08) and reproduces the median var/mean, not its variation.
- **Conversion noise ignored.** The number of light photons produced by each X-ray in the scintillator varies; this extra noise is not modelled, and units stay X-ray quanta through stage 3. g is therefore an effective gain, and the simulated quanta are effective quanta, not X-ray photons.
- **Offset and read noise on the binned grid.** Physically they act on each physical pixel before binning. Adding them after binning, with the values measured on the binned data, reproduces the measured statistics without having to infer unmeasurable physical-pixel values.
- **Gain map known only on the binned grid.** The four physical pixels of a 2×2 block share the same gain; after binning this is indistinguishable from the real detector.
- **Defects placed where their mechanism acts.** Dead and low-gain pixels are gain defects (stage 4, physical grid); hot pixels are dark-signal defects (stage 6, binned grid). The ground truth used by the tests is a map on the binned grid.
- **Flat drift as a single factor.** The second flat is the first multiplied by 1.0064; the object-shaped part (residual image) is not simulated.
- **Single quantisation step at the end.** Whether hardware binning happens before or after digitisation is unknown. Rounding adds 0.289 ADU, not negligible against the 0.542 ADU read noise, so it is subtracted in quadrature from the measured σ_read.
- **Not simulated**: residual image (lag), including the slow column variation of the dark that follows it; offset drift between orbits.

### Assumptions the simulator cannot test

The simulator is built on these assumptions, so its results cannot confirm them; they are checked, where possible, on real data.

- **Gain acts after the blur.** On simulated data the flat-field correction is exact by construction and its residual measures only the noise; the real test of the correction remains the walnut data.
- **Mean binning.** The public datasheet does not state whether the 2×2 binning is a mean or a sum; with a sum, g would be 4 times smaller.
- **Gaussian PSF.** σ_blur comes from the neighbour correlation. The correlation between adjacent row means (0.569) is higher than the neighbour correlation (0.50), which a Gaussian PSF would make equal: there is extra correlation over a few pixels (PSF tails or residual drift), to compare with the measured MTF in Milestone 5.
- **Linear, shift-invariant blur.** One σ for the whole detector, while the incidence is oblique up to ~30° on one side; the MTF will be measured near the centre.

### Implementation

- [`src/xray_detector_chain/params.py`](src/xray_detector_chain/params.py): `load_params()` reads the JSON and npz files of `params/`.
- [`src/xray_detector_chain/simulator.py`](src/xray_detector_chain/simulator.py): one function per stage (`mean_quanta`, `quantum_noise`, `blur`, `apply_gain`, `bin_mean`, `offset_map`, `read_noise`, `digitize`) and the grid change `to_physical`. The fixed offset map is drawn once; quantum and read noise are drawn for every frame from one random generator, so a run is reproducible and two frames have different noise.

### Validation

Tests in [`tests/`](tests/) run in CI. Done so far:
- Each stage against values computed by hand or from formulas: 2×2 mean binning, quanta from ADU, Poisson statistics, Gaussian blur (variance kept 1/(4πσ²) = 0.068, neighbour correlation 0.807 on the physical grid), gain, offset map. Without noise and blur the chain returns beam × (1 + gain map).
- Variance–mean slope of a uniform simulated flat: g = 0.110 without blur and binning, g/4 with binning only, g/4 × R_blur ≈ 0.0061 with both.
- Simulated darks: std of row-to-row jumps 12.34 ADU; σ_read from the difference of two darks 0.542 ADU (0.459 electronic + 0.289 rounding). Rounding adds 1/√12 even with σ = 0.459 because the per-pixel offset spreads the fractional parts uniformly.
- Parameter files: shapes, units, stages, and the cleaned gain map.

Planned: complete simulated darks and flat pairs analysed with the same functions as the real data, compared with the `targets`:
- median var/mean of d in 16×16 blocks: 0.0061 measured; the simulator is expected to give 0.00614 because σ_blur is rounded to 1.08 (R_blur 0.2234 instead of 0.222 at 1.085);
- neighbour correlation rho_1 ≈ 0.50; per-pixel offset ≈ 1.20 ADU; even/odd column offset ≈ 2.23 ADU;
- std of row-to-row jumps of d ≈ 0.53 ADU; robust spread of the relative gain pattern ≈ 0.47 %.

## Out of scope

- Correction of the residual image (lag): observed and quantified, not corrected or simulated.
- Offset drift between orbits (measured: up to 22 ADU), not simulated or corrected.
- DQE (only if time allows).

## Roadmap

- [x] 1. Data exploration
- [ ] 2. Detector simulator with known ground truth (parameters measured, stages 1–8 implemented and tested; validation of complete frames against the targets next)
- [ ] 3. Calibration: offset/gain correction, conversion gain, defective pixels
- [ ] 4. Filtering: noise/sharpness trade-off measured with NPS and MTF
- [ ] 5. Image quality: SNR, CNR, NPS, slanted-edge MTF against an analytic reference
- [ ] 6. MATLAB reference implementation, verified by Python tests in CI
- [ ] 7. DICOM export, report, release v1.0

## Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml`, `uv.lock`).

```bash
uv sync                  # creates .venv, installs the locked dependencies and the package (editable)
uv run jupyter lab       # opens the notebooks
uv run pytest            # runs the tests (no dataset needed: parameters are in params/)
uv run ruff check .      # lint, also run in CI
```

Data are not included in the repository. Download `Walnut1.zip` from Zenodo (DOI [10.5281/zenodo.2686725](https://doi.org/10.5281/zenodo.2686725)) and extract `Walnut1/Projections/tubeV1/`, plus the darks `tubeV2/di000000.tif` and `tubeV3/di000000.tif` into sibling folders of `tubeV1`. Set `DATA` in the first code cell of each notebook to the `tubeV1` folder.

## References

- Der Sarkissian H., Lucka F., van Eijnatten M., Colacicco G., Coban S. B., Batenburg K. J. *A cone-beam X-ray CT data collection designed for machine learning*. Scientific Data, 2019. [arXiv:1905.04787](https://arxiv.org/abs/1905.04787)