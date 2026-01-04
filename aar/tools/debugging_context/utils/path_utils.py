from pathlib import Path


def normalize_path(path: Path | str) -> Path:
    return Path(path).resolve()


def ensure_dir_exists(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
