import numpy as np
import cv2
from src import processing


def make_dummy_frame(w=100, h=80):
    # simple gradient image
    img = np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def test_apply_roi_and_signal():
    frame = make_dummy_frame(50, 40)
    # roi inside
    roi = (5, 5, 20, 10)
    sub = processing.apply_roi(frame, roi)
    assert sub.shape[0] == 10 and sub.shape[1] == 20

    val = processing.compute_frame_signal(sub, method='mean')
    assert val >= 0


def test_magnify_frame_fallback():
    frame = make_dummy_frame(30, 20)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # magnify_engine is None -> should return same-ish array
    out = processing.magnify_frame(None, gray, alpha=100, lambda_c=50)
    assert out.shape == gray.shape


def test_process_frame_basic():
    frame = make_dummy_frame(40, 30)
    params = {'roi': (0, 0, 20, 10), 'method': 'mean', 'magnify_engine': None}
    res = processing.process_frame(frame, params)
    assert 'processed_frame' in res and 'signal' in res and 'metadata' in res
    assert isinstance(res['signal'], float)
    pf = res['processed_frame']
    # processed frame should have same 2D shape as ROI
    assert pf.shape == (10, 20)
