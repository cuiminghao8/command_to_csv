from __future__ import annotations

import pytest

from cmd2csv.parser_pipeline import (
    fallback_whitespace,
    flatten_one_level,
    genie_to_rows,
    normalize_command,
    template_filename,
    utc_timestamp,
)


class TestNormalizeCommand:
    @pytest.mark.parametrize(
        "cmd, expected",
        [
            ("show ip int brief", "show_ip_int_brief"),
            ("  show   ip  bgp  summary  ", "show_ip_bgp_summary"),
            ("SHOW ARP", "show_arp"),
            ("show interface | include Ethernet", "show_interface_include_ethernet"),
            ("show/vlan\\stuff", "show_vlan_stuff"),
        ],
    )
    def test_normalizes_command(self, cmd, expected):
        assert normalize_command(cmd) == expected


class TestFlattenOneLevel:
    def test_flat_input_untouched(self):
        assert flatten_one_level({"a": 1, "b": "x"}) == {"a": 1, "b": "x"}

    def test_nested_dict_flattened_with_prefix(self):
        result = flatten_one_level({"vlan": {"id": 10, "name": "sales"}, "state": "up"})
        assert result == {"vlan_id": 10, "vlan_name": "sales", "state": "up"}


class TestGenieToRows:
    def test_list_of_dicts_returned_as_is(self):
        parsed = [{"a": 1}, {"a": 2}]
        assert genie_to_rows(parsed) is parsed

    def test_key_to_dict_becomes_rows_with_key(self):
        parsed = {"Gi0/0": {"state": "up"}, "Gi0/1": {"state": "down"}}
        rows = genie_to_rows(parsed)
        assert rows is not None
        assert {r["_key"] for r in rows} == {"Gi0/0", "Gi0/1"}
        assert all("state" in r for r in rows)

    def test_scalar_only_dict_returns_none(self):
        assert genie_to_rows({"a": 1}) is None

    def test_empty_returns_none(self):
        assert genie_to_rows({}) is None
        assert genie_to_rows([]) is None


class TestFallbackWhitespace:
    def test_splits_columns(self):
        raw = "R1    up   10.0.0.1\nR2    down 10.0.0.2\n"
        rows = fallback_whitespace(raw)
        assert rows == [
            {"col1": "R1", "col2": "up", "col3": "10.0.0.1"},
            {"col1": "R2", "col2": "down", "col3": "10.0.0.2"},
        ]

    def test_blank_lines_skipped(self):
        assert fallback_whitespace("\n\n") == []


class TestTemplateFilename:
    def test_pattern(self):
        assert (
            template_filename("cisco_ios", "show ip interface brief")
            == "cisco_ios__show_ip_interface_brief.textfsm"
        )


class TestTimestamp:
    def test_has_timezone(self):
        ts = utc_timestamp()
        assert "T" in ts
        assert ts.endswith("+00:00") or ts.endswith("Z")
