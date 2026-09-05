from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import config
from tools.system import startup_command


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_icons_exist_with_expected_sizes(self):
        self.assertTrue((ROOT / "assets" / "naty_source.png").is_file())
        for size in (16, 32, 48, 128, 256):
            path = ROOT / "assets" / f"naty_{size}.png"
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (size, size))
        with Image.open(ROOT / "assets" / "naty.ico") as image:
            self.assertTrue({16, 32, 48, 128, 256}.issubset({item[0] for item in image.info["sizes"]}))

    def test_spec_is_onedir_and_does_not_bundle_personal_config(self):
        spec = (ROOT / "naty.spec").read_text(encoding="utf-8")
        self.assertIn("COLLECT(", spec)
        self.assertIn("naty.ico", spec)
        self.assertIn("libvosk.dll", spec)
        self.assertIn("asset_names", spec)
        self.assertNotIn("config.toml", spec)

        core_spec = (ROOT / "naty_core.spec").read_text(encoding="utf-8")
        self.assertIn('name="Naty.Core"', core_spec)
        self.assertIn("COLLECT(", core_spec)
        self.assertNotIn("config.toml", core_spec)

    def test_frozen_startup_command_has_no_duplicate_executable(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", r"C:\Apps\NATY\Naty.exe"):
            command = startup_command()
        self.assertEqual(command.lower().count("naty.exe"), 1)

    def test_frozen_user_data_is_local_and_outside_installation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(sys, "frozen", True, create=True), patch.object(config.os, "name", "nt"), patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}):
                root = config.user_data_root()
            self.assertEqual(root, Path(temp_dir) / "NATY")

    def test_windows_installers_do_not_reference_obsidian(self):
        install = (ROOT / "packaging" / "install_naty.ps1").read_text(encoding="utf-8")
        uninstall = (ROOT / "packaging" / "uninstall_naty.ps1").read_text(encoding="utf-8")
        self.assertNotIn("obsidian_vault", (install + uninstall).lower())
        self.assertNotIn("userprofile", (install + uninstall).lower())
        self.assertIn('"Programs\\NATY"', install)
        self.assertIn('Assets\\naty.ico', install)
        self.assertIn('ie4uinit.exe', install)

    def test_hybrid_build_and_installer_contract(self):
        build = (ROOT / "scripts" / "build_windows.py").read_text(encoding="utf-8")
        installer = (ROOT / "packaging" / "Naty.iss").read_text(encoding="utf-8")
        uninstall = (ROOT / "packaging" / "uninstall_naty.ps1").read_text(encoding="utf-8")
        desktop = (ROOT / "desktop" / "Naty.Desktop" / "Naty.Desktop.csproj").read_text(encoding="utf-8")
        client = (ROOT / "desktop" / "Naty.Desktop" / "Services" / "CoreClient.cs").read_text(encoding="utf-8")
        self.assertIn('"Naty.exe"', build)
        self.assertIn('"Naty.Core.exe"', build)
        self.assertIn("--self-contained", build)
        self.assertIn("NatyHybrid", installer)
        self.assertIn("OutputBaseFilename=NatySetup", installer)
        self.assertIn("<AssemblyName>Naty</AssemblyName>", desktop)
        self.assertIn('"Core", "Naty.Core.exe"', client)
        self.assertNotIn("Remove-Item -LiteralPath $dataRoot", uninstall)
        self.assertNotIn("{localappdata}\\NATY", installer.split("[UninstallDelete]")[-1] if "[UninstallDelete]" in installer else "")


if __name__ == "__main__":
    unittest.main()
