"""Read the simulator parameters written by notebooks/02_simulator_parameters.ipynb."""

import json
from pathlib import Path

import numpy as np

# repository root / params: this file is src/xray_detector_chain/params.py, three levels below the root.
# Valid because uv installs the package in editable mode (the code stays in the repository).
PARAMS_DIR = Path(__file__).resolve().parents[2] / "params"


def load_params(name="walnut_tubeV1", params_dir=PARAMS_DIR):
    """Return (scalars, maps) for one parameter set.

    scalars: dict with sections "meta", "true" and "targets". Every entry of "true" and "targets"
        is a dict with keys "value", "unit", "stage" and "source".
        Example: scalars["true"]["g"]["value"] -> 0.11 (ADU per quantum, physical pixel).
    maps: dict of NumPy arrays from the npz file:
        "row_offsets" (768,) ADU, "col_offsets" (972,) ADU,
        "gain_rel" (768, 972) fraction (0.01 = +1 %), "beam" (768, 972) ADU.
    """
    params_dir = Path(params_dir)
    scalars = json.loads((params_dir / f"{name}.json").read_text())
    with np.load(params_dir / f"{name}_maps.npz") as npz:  # "with" closes the file after reading
        maps = {key: npz[key] for key in npz.files}
    return scalars, maps
