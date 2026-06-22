from datetime import datetime
from pathlib import Path


class ActivityLog:
    def __init__(self, log_file_path: str | Path):
        self.log_file_path = Path(log_file_path)

    def record(self, message: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}"

        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file_path.open("a", encoding="utf-8") as log_file:
            log_file.write(entry + "\n")

        return entry
