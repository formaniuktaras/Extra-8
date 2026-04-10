from __future__ import annotations

from pathlib import Path

from core.settings import SettingsManager, UserSettings, encode_bytes
from services.settings_service import SettingsService


def test_window_state_persistence_roundtrip(tmp_path: Path):
    mgr = SettingsManager(tmp_path)
    settings = UserSettings(
        window_geometry_b64=encode_bytes(b"geom"),
        window_state_b64=encode_bytes(b"state"),
        splitter_states_b64={"a": encode_bytes(b"split")},
        last_selected_tab=1,
        last_search_text="foo",
    )
    mgr.save(settings)
    loaded = mgr.load()
    assert loaded.window_geometry_b64 == settings.window_geometry_b64
    assert loaded.window_state_b64 == settings.window_state_b64
    assert loaded.splitter_states_b64["a"] == settings.splitter_states_b64["a"]


def test_recent_paths_bounded_and_deduplicated(tmp_path: Path):
    service = SettingsService(SettingsManager(tmp_path))
    for i in range(15):
        service.add_recent_source_dir(f"/tmp/source-{i}")
    service.add_recent_source_dir("/tmp/source-14")
    assert len(service.settings.recent_source_dirs) == 10
    assert service.settings.recent_source_dirs[0] == "/tmp/source-14"
    assert service.settings.recent_source_dirs.count("/tmp/source-14") == 1


def test_path_fields_roundtrip(tmp_path: Path):
    mgr = SettingsManager(tmp_path)
    st = UserSettings(recent_source_dirs=["a"], recent_output_dirs=["b"], recent_index_files=["c"])
    mgr.save(st)
    loaded = mgr.load()
    assert loaded.recent_source_dirs == ["a"]
    assert loaded.recent_output_dirs == ["b"]
    assert loaded.recent_index_files == ["c"]
