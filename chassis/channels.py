from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Channel(Protocol):
    name: str

    def send(self, destination: str, body: str) -> None: ...


class ConsoleChannel:
    name = "console"

    def send(self, destination: str, body: str) -> None:
        print(f"[{destination}] {body}")


class FileChannel:
    name = "file"

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def send(self, destination: str, body: str) -> None:
        safe = destination.replace("/", "_").replace(":", "_")
        path = self.root / f"{safe}.txt"
        path.write_text(body, encoding="utf-8")
