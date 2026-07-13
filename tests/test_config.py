from __future__ import annotations

from cmd2csv.config import _coerce_list, load_config, load_lines


class TestCoerceList:
    def test_none_is_empty(self):
        assert _coerce_list(None) == []

    def test_list_stripped_and_filtered(self):
        assert _coerce_list([" a ", "", "b"]) == ["a", "b"]

    def test_comma_string_split(self):
        assert _coerce_list("a, b, ,c") == ["a", "b", "c"]


class TestLoadLines:
    def test_ignores_blank_and_comments(self, tmp_path):
        p = tmp_path / "hosts.txt"
        p.write_text("R1\n# a comment\n\nR2\n  R3  \n", encoding="utf-8")
        assert load_lines(str(p)) == ["R1", "R2", "R3"]


class TestLoadConfig:
    def test_minimal(self, tmp_path):
        p = tmp_path / "cfg.yaml"
        p.write_text(
            """
hosts: R1,R2
commands:
  - show ip int brief
  - show version
ndb_url: https://ndb.example.com/api
ndb_token: abc
username: admin
formats: csv,json
workers: 8
email:
  enabled: true
  smtp_server: smtp.example.com
  sender: net@example.com
  recipients: [ops@example.com]
""",
            encoding="utf-8",
        )
        cfg = load_config(str(p))
        assert cfg.hosts == ["R1", "R2"]
        assert cfg.commands == ["show ip int brief", "show version"]
        assert cfg.ndb_url == "https://ndb.example.com/api"
        assert cfg.username == "admin"
        assert cfg.formats == ["csv", "json"]
        assert cfg.workers == 8
        assert cfg.email.enabled is True
        assert cfg.email.smtp_server == "smtp.example.com"
        assert cfg.email.recipients == ["ops@example.com"]

    def test_defaults(self, tmp_path):
        p = tmp_path / "cfg.yaml"
        p.write_text("hosts: R1\ncommands: show ver\n", encoding="utf-8")
        cfg = load_config(str(p))
        assert cfg.output_dir == "output"
        assert cfg.formats == ["csv"]
        assert cfg.workers == 4
        assert cfg.email.enabled is False
