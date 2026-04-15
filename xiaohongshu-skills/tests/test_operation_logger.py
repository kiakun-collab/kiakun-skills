from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import operation_logger


class OperationLoggerTest(unittest.TestCase):
    def test_start_and_finish_command_persist_run_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_root = Path(tmpdir)
            with mock.patch.object(operation_logger, "_LOG_ROOT", log_root), mock.patch.object(
                operation_logger.uuid, "uuid4"
            ) as mock_uuid:
                mock_uuid.return_value.hex = "abcdef1234567890"
                metadata = operation_logger.start_command("search-feeds", "brand-a", {"keyword": "露营"})
                operation_logger.finish_command(
                    metadata["run_id"],
                    exit_code=0,
                    result={"success": True},
                    failure_artifacts={},
                )

            payload = (Path(metadata["run_dir"]) / "run.json").read_text(encoding="utf-8")
            self.assertIn('"command": "search-feeds"', payload)
            self.assertIn('"status": "success"', payload)


if __name__ == "__main__":
    unittest.main()
