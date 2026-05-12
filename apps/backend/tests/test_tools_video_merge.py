import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import PropertyMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.source import Source
from app.db.models.tool_run import ToolRun
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app
from app.services.tools import video_merge
from app.services.tools.service import ToolsService
from app.services.tools.video_merge import VideoMergeRunner, choose_non_overwriting_path, normalize_output_name


def _dt(hour: int = 10) -> datetime:
    return datetime(2026, 5, 1, hour, tzinfo=UTC).replace(tzinfo=None)


class ToolsVideoMergeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_get_tools_returns_video_merge(self) -> None:
        with TestClient(app) as client:
            response = client.get("/tools")

        self.assertEqual(200, response.status_code)
        self.assertEqual(["video_merge"], [item["key"] for item in response.json()["items"]])

    def test_start_rejects_single_input(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/tools/video-merge/runs",
                json={
                    "inputs": [{"source_kind": "external_path", "path": "G:/video/a.mp4"}],
                    "output_name": "merged",
                    "mode": "copy",
                },
            )

        self.assertEqual(422, response.status_code)

    def test_rejects_non_video_external_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "notes.txt"
            path.write_text("not video", encoding="utf-8")
            with TestClient(app) as client:
                response = client.post(
                    "/tools/video-merge/runs",
                    json={
                        "inputs": [
                            {"source_kind": "external_path", "path": str(path)},
                            {"source_kind": "external_path", "path": str(path)},
                        ],
                        "output_name": "merged",
                        "mode": "copy",
                    },
                )

        self.assertEqual(400, response.status_code)
        self.assertEqual("VIDEO_MERGE_INVALID", response.json()["error"]["code"])

    def test_resolves_indexed_video_and_creates_pending_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "a.mp4"
            second = Path(temp_dir) / "b.mp4"
            first.write_bytes(b"a")
            second.write_bytes(b"b")
            first_id = self._seed_file(first, "video")
            second_id = self._seed_file(second, "video")
            with patch("app.services.tools.service.threading.Thread") as thread_class:
                thread_class.return_value.start.return_value = None
                with TestClient(app) as client:
                    response = client.post(
                        "/tools/video-merge/runs",
                        json={
                            "inputs": [
                                {"source_kind": "indexed_file", "file_id": first_id},
                                {"source_kind": "indexed_file", "file_id": second_id},
                            ],
                            "output_name": "merged",
                            "mode": "copy",
                        },
                    )

        self.assertEqual(200, response.status_code)
        self.assertEqual("pending", response.json()["status"])
        with SessionLocal() as session:
            run = session.get(ToolRun, response.json()["run_id"])
            self.assertIsNotNone(run)
            self.assertEqual("pending", run.status)
            self.assertTrue(json.loads(run.input_json)["planned_output_path"].endswith("merged.mp4"))

    def test_filename_and_overwrite_helpers(self) -> None:
        self.assertEqual("clip.mp4", normalize_output_name("clip"))
        with self.assertRaisesRegex(Exception, "invalid"):
            normalize_output_name("bad:name.mp4")
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "final.mp4"
            existing.write_bytes(b"exists")
            self.assertEqual(Path(temp_dir) / "final_1.mp4", choose_non_overwriting_path(Path(temp_dir), "final.mp4"))

    def test_runner_builds_copy_and_reencode_commands(self) -> None:
        runner = VideoMergeRunner()
        copy_command = runner._build_command("ffmpeg", Path("list.txt"), Path("out.mp4"), "copy")
        reencode_command = runner._build_command("ffmpeg", Path("list.txt"), Path("out.mp4"), "reencode")
        self.assertIn("-c", copy_command)
        self.assertIn("copy", copy_command)
        self.assertIn("libx264", reencode_command)
        self.assertIn("aac", reencode_command)

    def test_runner_uses_bytes_decode_shell_false_and_copy_failure_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "a.mp4"
            second = Path(temp_dir) / "b.mp4"
            output = Path(temp_dir) / "out.mp4"
            first.write_bytes(b"a")
            second.write_bytes(b"b")
            captured = {}

            def fake_run(command, **kwargs):
                captured["command"] = command
                captured["kwargs"] = kwargs
                return type("Completed", (), {"returncode": 1, "stdout": b"", "stderr": b"\x80bad stream"})()

            with patch.object(VideoMergeRunner, "_resolve_ffmpeg_path", return_value="ffmpeg"):
                with patch.object(type(video_merge.settings), "data_dir", new_callable=PropertyMock) as data_dir_mock:
                    data_dir_mock.return_value = Path(temp_dir)
                    with patch("app.services.tools.video_merge.subprocess.run", side_effect=fake_run):
                        with self.assertRaisesRegex(Exception, "Compatible merge"):
                            VideoMergeRunner().execute(
                                run_id=12345,
                                inputs=[
                                    video_merge.VideoMergeResolvedInput("external_path", first),
                                    video_merge.VideoMergeResolvedInput("external_path", second),
                                ],
                                output_path=output,
                                mode="copy",
                            )

        self.assertFalse(captured["kwargs"]["shell"])
        self.assertIsInstance(captured["command"], list)

    def test_startup_marks_stale_runs_failed(self) -> None:
        now = _dt()
        with SessionLocal() as session:
            session.add(
                ToolRun(
                    tool_key="video_merge",
                    status="running",
                    input_json="{}",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()
            ToolsService().mark_stale_runs_failed(session)
            run = session.query(ToolRun).one()
            self.assertEqual("failed", run.status)
            self.assertIn("interrupted", run.error_message)

    def test_log_tail_is_limited(self) -> None:
        now = _dt()
        with SessionLocal() as session:
            run = ToolRun(
                tool_key="video_merge",
                status="failed",
                input_json="{}",
                log_text="x" * 25_000,
                error_message="failed",
                created_at=now,
                updated_at=now,
            )
            session.add(run)
            session.commit()
            run_id = run.id
            with TestClient(app) as client:
                response = client.get(f"/tools/runs/{run_id}")

        self.assertEqual(200, response.status_code)
        self.assertEqual(20_000, len(response.json()["log_tail"]))

    def _seed_file(self, path: Path, file_type: str) -> int:
        now = _dt()
        with SessionLocal() as session:
            source = session.query(Source).filter(Source.path == str(path.parent)).one_or_none()
            if source is None:
                source = Source(
                    path=str(path.parent),
                    display_name="Temp",
                    is_enabled=True,
                    scan_mode="manual_plus_basic_incremental",
                    last_scan_at=None,
                    last_scan_status=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(source)
                session.flush()
            file = File(
                source_id=source.id,
                path=str(path),
                parent_path=str(path.parent),
                name=path.name,
                stem=path.stem,
                extension=path.suffix.lstrip("."),
                file_type=file_type,
                mime_type=None,
                size_bytes=path.stat().st_size,
                created_at_fs=now,
                modified_at_fs=now,
                discovered_at=now,
                last_seen_at=now,
                is_deleted=False,
                checksum_hint=None,
                updated_at=now,
            )
            session.add(file)
            session.commit()
            return file.id

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM tool_runs"))
            session.execute(text("DELETE FROM tasks"))
            session.execute(text("DELETE FROM file_metadata"))
            session.execute(text("DELETE FROM file_tags"))
            session.execute(text("DELETE FROM file_user_meta"))
            session.execute(text("DELETE FROM files"))
            session.execute(text("DELETE FROM source_ignore_rules"))
            session.execute(text("DELETE FROM tags"))
            session.execute(text("DELETE FROM sources"))
            session.commit()


if __name__ == "__main__":
    unittest.main()
