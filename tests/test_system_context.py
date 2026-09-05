from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

import psutil

from nlu import intents
from nlu.parser import RuleParser
from system_context.snapshot import SystemContextProvider, SystemSnapshot
from tools.system_status import SystemStatusTool


class FakeProvider:
    def __init__(self, snapshot): self.snapshot = snapshot
    def collect(self): return self.snapshot


def sample(**changes):
    base = SystemSnapshot(
        "2026-09-05T10:00:00-03:00", cpu_percent=20,
        memory={"total_mib": 16384, "used_mib": 8192, "available_mib": 8192, "percent": 50},
        disk={"total_mib": 1000, "used_mib": 500, "free_mib": 500, "percent": 50},
        top_processes=[{"pid": 10, "name": "editor.exe", "ram_mib": 500}],
        naty_process_tree={"processes": 2, "names": ["Naty.exe", "Naty.Core.exe"], "ram_mib": 190},
    )
    return replace(base, **changes)


class SystemContextTests(unittest.TestCase):
    def test_system_intents_are_specific(self):
        parser = RuleParser()
        self.assertEqual(intents.SYSTEM_STATUS, parser.parse("Naty, como está meu computador?").name)
        self.assertEqual("top_memory", parser.parse("O que está usando mais RAM?").entities["focus"])
        self.assertEqual(intents.SYSTEM_DIAGNOSIS, parser.parse("Meu PC está lento.").name)

    def test_status_exposes_valid_metrics_and_ui(self):
        result = SystemStatusTool(FakeProvider(sample())).status("memory")
        self.assertTrue(result.ok)
        self.assertIn("50%", result.message)
        self.assertEqual("system", result.ui_hint["panel"])
        self.assertLessEqual(len(result.data["top_processes"]), 5)

    def test_diagnosis_uses_evidence_without_claiming_a_cause(self):
        result = SystemStatusTool(FakeProvider(sample(cpu_percent=96))).status(diagnose=True)
        self.assertIn("CPU está em 96%", result.message)
        self.assertNotIn("vírus", result.message.casefold())

    def test_missing_process_and_provider_errors_do_not_escape(self):
        with patch("system_context.snapshot.psutil.cpu_percent", side_effect=RuntimeError), \
             patch("system_context.snapshot.psutil.virtual_memory", side_effect=RuntimeError), \
             patch("system_context.snapshot.psutil.Process", side_effect=psutil.NoSuchProcess(999999)):
            snapshot = SystemContextProvider(999999).collect()
        self.assertIsNone(snapshot.cpu_percent)
        self.assertEqual("unavailable", snapshot.memory["state"])
        self.assertEqual("unavailable", snapshot.naty_process_tree["state"])


if __name__ == "__main__": unittest.main()
