from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

sys.modules.setdefault("requests", mock.MagicMock())
websockets_module = sys.modules.setdefault("websockets", types.ModuleType("websockets"))
sync_module = sys.modules.setdefault("websockets.sync", types.ModuleType("websockets.sync"))
client_module = sys.modules.setdefault("websockets.sync.client", types.ModuleType("websockets.sync.client"))
setattr(client_module, "connect", mock.MagicMock())
setattr(sync_module, "client", client_module)
setattr(websockets_module, "sync", sync_module)

import account_manager
import runtime_state
from xhs.cdp import _select_all_modifier_value


class RuntimeGuardsTest(unittest.TestCase):
    def test_select_all_modifier_matches_platform(self) -> None:
        self.assertEqual(_select_all_modifier_value("Darwin"), 4)
        self.assertEqual(_select_all_modifier_value("Linux"), 2)

    def test_profile_dir_uses_default_account_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            accounts_file = config_dir / "accounts.json"
            accounts_file.write_text(
                '{"default": "brand-a", "accounts": {"brand-a": {"description": ""}}}',
                encoding="utf-8",
            )

            with mock.patch.object(account_manager, "_CONFIG_DIR", config_dir), mock.patch.object(
                account_manager, "_ACCOUNTS_FILE", accounts_file
            ), mock.patch.object(account_manager, "_DEFAULT_PROFILE_DIR", config_dir / "chrome-profile"):
                profile_dir = account_manager.get_profile_dir("")

            self.assertEqual(profile_dir, str(config_dir / "accounts" / "brand-a" / "chrome-profile"))

    def test_runtime_state_is_namespaced_by_port_and_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir)
            with mock.patch.object(runtime_state, "_RUNTIME_DIR", runtime_dir):
                runtime_state.save_active_page(
                    9222,
                    "brand-a",
                    "target-123",
                    flow="image-publish",
                    stage="awaiting-publish",
                )
                state = runtime_state.load_active_page(9222, "brand-a")
                self.assertIsNotNone(state)
                assert state is not None
                self.assertEqual(state["target_id"], "target-123")
                self.assertEqual(state["flow"], "image-publish")

                runtime_state.clear_active_page(9222, "brand-a")
                self.assertIsNone(runtime_state.load_active_page(9222, "brand-a"))


if __name__ == "__main__":
    unittest.main()
