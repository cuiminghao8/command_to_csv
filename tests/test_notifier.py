from __future__ import annotations

from cmd2csv.config import EmailConfig
from cmd2csv.notifier import send_email


class TestSendEmail:
    def test_disabled_returns_false(self):
        cfg = EmailConfig(enabled=False)
        assert send_email(cfg, "body") is False

    def test_missing_config_returns_false(self):
        cfg = EmailConfig(enabled=True)
        assert send_email(cfg, "body") is False


class TestSummaryReport:
    def test_report_labels_devices(self):
        from cmd2csv.runner import DeviceResult, RunSummary

        summary = RunSummary(
            entities={"show_arp": [{"hostname": "R1"}]},
            results=[
                DeviceResult(hostname="R1", ok=True, commands_ok=2, elapsed=1.2),
                DeviceResult(
                    hostname="R2",
                    ok=False,
                    commands_ok=1,
                    commands_failed=1,
                    error=None,
                    command_errors={"show ver": "timeout"},
                ),
            ],
        )
        text = summary.format_report()
        assert "devices ok:     1" in text
        assert "devices failed: 1" in text
        assert "R1" in text and "R2" in text
        assert "timeout" in text
