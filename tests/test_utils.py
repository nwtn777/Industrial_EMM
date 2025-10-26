import os
import json
import tempfile
import csv

import pytest

from src import logger
from src import utils


def test_load_and_save_config(tmp_path):
    cfg = utils.load_config()
    # modify and save to a temp file
    cfg['default_settings']['fps'] = 12.5
    p = tmp_path / "temp_config.json"
    assert utils.save_config(cfg, str(p)) is True

    # load back
    loaded = utils.load_config(str(p))
    assert loaded['default_settings']['fps'] == 12.5


def test_validate_roi_and_format_time_duration():
    frame_shape = (480, 640, 3)
    assert utils.validate_roi((10, 10, 50, 50), frame_shape) is True
    assert utils.validate_roi(( -1, 0, 50, 50), frame_shape) is False
    assert utils.validate_roi(None, frame_shape) is False

    assert utils.format_time_duration(5) == "5.0s"
    assert "m" in utils.format_time_duration(65)
    assert "h" in utils.format_time_duration(3600)


def test_export_signal_data(tmp_path):
    signal = [0.1, 0.2, 0.3]
    times = [0, 1, 2]
    out = tmp_path / "signal.csv"
    ok, fname = utils.export_signal_data(signal, times, filename=str(out))
    assert ok is True
    assert os.path.exists(fname)

    # simple CSV content check
    with open(fname, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows[0] == ['Time', 'Signal']
    assert len(rows) == 4


def test_performance_monitor():
    pm = utils.PerformanceMonitor()
    pm.record_frame_time(0.02)
    pm.record_frame_time(0.03)
    pm.record_processing_time(0.01)
    stats = pm.get_performance_stats()
    assert 'avg_fps' in stats
    assert stats['total_frames'] == 2
