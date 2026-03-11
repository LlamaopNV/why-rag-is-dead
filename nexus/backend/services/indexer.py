import os
from pathlib import Path
from typing import Optional

from backend.models.schemas import IndexResponse

IGNORED_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".mypy_cache", "dist", "build",
    ".pytest_cache", ".tox", ".eggs", "*.egg-info",
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".swift", ".kt", ".cs",
    ".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg",
}


class CodebaseIndexer:
    def __init__(self):
        self.codebase_path: Optional[Path] = None
        self.file_index: dict[str, dict] = {}  # rel_path -> {lines, size, extension, abs_path}
        self.total_lines: int = 0
        self.indexed: bool = False

    def index(self, path: str) -> IndexResponse:
        root = Path(path).resolve()
        if not root.exists():
            raise ValueError(f"Path does not exist: {path}")

        self.codebase_path = root
        self.file_index = {}
        self.total_lines = 0
        extensions: dict[str, int] = {}

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune in-place so os.walk skips ignored dirs
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

            for filename in filenames:
                filepath = Path(dirpath) / filename
                ext = filepath.suffix.lower()
                if ext not in CODE_EXTENSIONS:
                    continue

                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    line_count = len(lines)
                    size = filepath.stat().st_size
                    rel_path = str(filepath.relative_to(root))

                    self.file_index[rel_path] = {
                        "lines": line_count,
                        "size": size,
                        "extension": ext,
                        "abs_path": str(filepath),
                    }
                    self.total_lines += line_count
                    extensions[ext] = extensions.get(ext, 0) + 1
                except Exception:
                    continue

        self.indexed = True
        return IndexResponse(
            path=str(root),
            file_count=len(self.file_index),
            total_lines=self.total_lines,
            extensions=extensions,
        )

    def get_file_list(self) -> list[str]:
        return sorted(self.file_index.keys())

    def get_file_tree(self, max_files: int = 500) -> str:
        """Compact newline-separated file list for use in prompts."""
        return "\n".join(self.get_file_list()[:max_files])

    def safe_path(self, rel_path: str) -> Optional[Path]:
        """Resolve and validate a relative path is inside the codebase root."""
        if not self.codebase_path:
            return None
        try:
            resolved = (self.codebase_path / rel_path).resolve()
            resolved.relative_to(self.codebase_path)  # raises ValueError if outside
            return resolved if resolved.exists() else None
        except ValueError:
            return None

    def naive_token_estimate(self) -> int:
        """Rough estimate of tokens if we dumped the whole codebase into context."""
        # ~4 chars per token on average for code
        total_chars = sum(info["size"] for info in self.file_index.values())
        return total_chars // 4


# Singleton — imported by other modules
indexer = CodebaseIndexer()
