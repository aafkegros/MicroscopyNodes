import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..data_model import DatasetModel


class LocalFileProcess:
    def __init__(self, dataset_model, blender_binary, package_name):
        if not blender_binary:
            raise ValueError("Blender executable path is unavailable")

        self.job_dir = Path(tempfile.mkdtemp(prefix="microscopynodes-local-files-"))
        self.process = None
        self.log_handle = None
        try:
            (self.job_dir / "request.json").write_text(
                dataset_model.model_dump_json(),
                encoding="utf-8",
            )
            self.log_handle = (self.job_dir / "worker.log").open("w", encoding="utf-8")
            worker_path = Path(__file__).with_name("local_file_worker.py")
            self.process = subprocess.Popen(
                [
                    blender_binary,
                    "--background",
                    "--python-exit-code", "1",
                    "--python", str(worker_path),
                    "--",
                    "--job-dir", str(self.job_dir),
                    "--package", package_name,
                ],
                stdout=self.log_handle,
                stderr=subprocess.STDOUT,
            )
        except Exception:
            self.close()
            raise

    def poll(self):
        return self.process.poll()

    def progress(self):
        progress_path = self.job_dir / "progress.txt"
        if not progress_path.exists():
            return None
        try:
            return progress_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def result(self):
        returncode = self.poll()
        if returncode is None:
            raise RuntimeError("Local-file worker is still running")
        if returncode != 0:
            raise RuntimeError(self.error())
        self._close_log()
        return DatasetModel.model_validate_json(
            (self.job_dir / "result.json").read_text(encoding="utf-8")
        )

    def error(self):
        self._close_log()
        error_path = self.job_dir / "error.json"
        if error_path.exists():
            try:
                return json.loads(error_path.read_text(encoding="utf-8"))["error"]
            except Exception:
                pass
        log_path = self.job_dir / "worker.log"
        if log_path.exists():
            log_tail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:].strip()
            if log_tail:
                return log_tail
        return f"Local-file worker exited with code {self.process.returncode}"

    def close(self):
        self._stop_process()
        self._close_log()
        if self.job_dir is not None:
            shutil.rmtree(self.job_dir, ignore_errors=True)
            self.job_dir = None

    def _stop_process(self):
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=1)

    def _close_log(self):
        if self.log_handle is None:
            return
        self.log_handle.close()
        self.log_handle = None
