from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from cmd2csv.exporter import _fieldnames_for, _stringify, export, export_csv, export_json


def sample_entities():
    return {
        "show_arp": [
            {
                "hostname": "R2",
                "site": "PEK",
                "role": "router",
                "os": "iosxe",
                "timestamp": "2026-07-13T00:00:00+00:00",
                "command": "show arp",
                "parse_engine": "ntc",
                "ip": "10.0.0.2",
                "mac": "aaaa.bbbb.cccc",
            },
            {
                "hostname": "R1",
                "site": "PEK",
                "role": "router",
                "os": "iosxe",
                "timestamp": "2026-07-13T00:00:00+00:00",
                "command": "show arp",
                "parse_engine": "ntc",
                "ip": "10.0.0.1",
                "mac": "aaaa.bbbb.dddd",
            },
        ]
    }


class TestFieldOrdering:
    def test_meta_fields_come_first(self):
        rows = [{"hostname": "R1", "custom_a": 1, "os": "ios", "z_extra": 2}]
        fields = _fieldnames_for(rows)
        assert fields[:2] == ["hostname", "os"]
        assert fields[2:] == sorted(["custom_a", "z_extra"])


class TestStringify:
    def test_scalar_pass_through(self):
        assert _stringify("x") == "x"
        assert _stringify(1) == 1
        assert _stringify(None) is None

    def test_dict_serialized_to_json(self):
        assert _stringify({"a": 1}) == '{"a": 1}'

    def test_list_serialized_to_json(self):
        assert _stringify([1, 2]) == "[1, 2]"


class TestExportCSV:
    def test_writes_one_file_per_entity(self, tmp_path):
        paths = export_csv(sample_entities(), str(tmp_path))
        assert len(paths) == 1
        p = Path(paths[0])
        assert p.name == "show_arp.csv"

        with p.open(newline="") as f:
            rows = list(csv.DictReader(f))
        assert [r["hostname"] for r in rows] == ["R1", "R2"]
        assert rows[0]["ip"] == "10.0.0.1"

    def test_empty_entities_write_nothing(self, tmp_path):
        assert export_csv({"empty": []}, str(tmp_path)) == []
        assert list(tmp_path.iterdir()) == []


class TestExportJSON:
    def test_writes_valid_json(self, tmp_path):
        paths = export_json(sample_entities(), str(tmp_path))
        data = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
        assert [row["hostname"] for row in data] == ["R1", "R2"]


class TestExportDispatch:
    def test_multi_format(self, tmp_path):
        paths = export(sample_entities(), str(tmp_path), formats=("csv", "json"))
        exts = sorted(Path(p).suffix for p in paths)
        assert exts == [".csv", ".json"]

    def test_unknown_format_raises(self, tmp_path):
        with pytest.raises(ValueError):
            export({}, str(tmp_path), formats=("xlsx",))
