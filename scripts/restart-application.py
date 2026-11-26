"""Stop only this checkout's managed app workers; keep Mongo/Kafka and data."""
import json
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / ".runtime" / "app-processes.json"


def main():
    entries = json.loads(PID_FILE.read_text("utf-8-sig")) if PID_FILE.exists() else {}
    for name, pid in entries.items():
        try:
            process = psutil.Process(pid)
            args = process.cmdline()
            if not Path(process.exe()).is_relative_to(ROOT) or not (
                "scholarship_map.cli" in args or "scholarship_map.api:app" in args
            ):
                raise RuntimeError(f"Refused unrelated/reused process ID for {name}")
            children = process.children(recursive=True)
            for child in reversed(children):
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            process.terminate()
            _, remaining = psutil.wait_procs(children + [process], timeout=3)
            for owned in remaining:
                try:
                    owned.kill()
                except psutil.NoSuchProcess:
                    pass
            print(f"Stopped project app worker: {name}")
        except psutil.NoSuchProcess:
            pass
    PID_FILE.write_text("{}\n", encoding="utf8")
    print("MongoDB, Kafka, stored records and checkpoints retained. Run Start-Project.ps1.")


if __name__ == "__main__":
    main()
