"""
Platform-aware bash discovery + async-safe shell execution.

asyncio.create_subprocess_exec requires ProactorEventLoop on Windows,
which conflicts with uvicorn's default loop.  We avoid the issue entirely
by running subprocess.run in a thread-pool executor — works on any loop.
"""
import asyncio
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_GIT_BASH_CANDIDATES = [
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
]

# WSL bash (C:\Windows\System32\bash.exe) does NOT reliably pipe stdout back
# to Python subprocess on all Windows configs — always prefer Git Bash.
def _find_bash() -> str:
    # 1. Git Bash — reliable, pipes stdout correctly
    for c in _GIT_BASH_CANDIDATES:
        if Path(c).exists():
            return c

    # 2. PATH lookup — but skip WSL bash if that's all it finds
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found

    # 3. Last resort: WSL bash (may work on some configs)
    wsl = r"C:\Windows\System32\bash.exe"
    if Path(wsl).exists():
        return wsl

    raise RuntimeError(
        "Git Bash not found. Install Git for Windows: https://gitforwindows.org"
    )


BASH = _find_bash()

# Shared thread pool — workers run shell commands concurrently
_POOL = ThreadPoolExecutor(max_workers=16, thread_name_prefix="nexus-shell")


async def run_shell(command: str, cwd: Path, timeout: float = 15.0) -> str:
    """
    Run a bash command in a thread-pool executor.
    Safe on any asyncio event loop (SelectorEventLoop or ProactorEventLoop).
    Returns stdout as a string, capped at 8 000 chars.
    """
    loop = asyncio.get_running_loop()

    def _run() -> str:
        result = subprocess.run(
            [BASH, "-c", command],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout,
        )
        return result.stdout[:8_000]

    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_POOL, _run),
            timeout=timeout + 2,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Shell command timed out: {command}")