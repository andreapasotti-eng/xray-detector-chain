import numpy as np

import xray_detector_chain


def test_import():
    assert xray_detector_chain is not None


def test_trappola_uint16():
    # Sottrarre in uint16 va in overflow: per questo si converte a float prima di correggere
    a = np.array([100], dtype=np.uint16)
    b = np.array([200], dtype=np.uint16)
    assert (a - b)[0] == 65436
    assert (a.astype(np.float32) - b)[0] == -100
