"""Cross-platform advisory file locks for repository scripts.

POSIX and Windows expose different standard-library locking APIs.  Keeping
that split here lets the data pipelines share one implementation without an
operating-system-specific copy of each script.
"""

from __future__ import annotations

import errno
import os
from dataclasses import dataclass
from pathlib import Path
from typing import IO

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class LockUnavailableError(OSError):
    """Raised when another process already holds an advisory file lock."""


@dataclass(frozen=True)
class LockSnapshot:
    """A non-mutating view of an advisory lock file."""

    path: Path
    exists: bool
    owner: str | None
    held: bool


def _is_contention_error(error: OSError) -> bool:
    return error.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}


def _ensure_windows_lock_byte(handle: IO[str]) -> None:
    """Ensure Windows has one byte to lock without changing existing markers."""

    if os.name != "nt":
        return
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write("\n")
        handle.flush()


def acquire_file_lock(handle: IO[str], *, prepare: bool = True) -> None:
    """Acquire an exclusive non-blocking lock for an open file handle."""

    if prepare:
        _ensure_windows_lock_byte(handle)
    handle.seek(0)
    try:
        if os.name == "nt":
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        if _is_contention_error(error):
            raise LockUnavailableError(str(error)) from error
        raise


def release_file_lock(handle: IO[str]) -> None:
    """Release a lock previously acquired with :func:`acquire_file_lock`."""

    handle.seek(0)
    if os.name == "nt":
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class InterProcessFileLock:
    """Context-managed exclusive advisory lock with optional owner metadata."""

    def __init__(self, path: Path, *, owner: str | None = None):
        self.path = Path(path)
        self.owner = owner
        self._handle: IO[str] | None = None

    def acquire(self) -> "InterProcessFileLock":
        if self._handle is not None:
            raise RuntimeError(f"lock is already acquired: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        acquired = False
        try:
            acquire_file_lock(handle)
            acquired = True
            if self.owner is not None:
                handle.seek(0)
                handle.truncate()
                # Byte zero belongs to the OS lock.  Windows denies reads that
                # overlap it, so owner metadata begins at byte one.
                handle.write(f"\n{self.owner}")
                handle.flush()
        except BaseException:
            try:
                if acquired:
                    release_file_lock(handle)
            finally:
                handle.close()
            raise
        self._handle = handle
        return self

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            release_file_lock(self._handle)
        finally:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "InterProcessFileLock":
        return self.acquire()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()


def inspect_file_lock(path: Path) -> LockSnapshot:
    """Inspect a lock without creating, deleting, or rewriting its marker."""

    resolved = Path(path).expanduser().resolve()
    try:
        with resolved.open("r+", encoding="utf-8") as handle:
            handle.seek(0, os.SEEK_END)
            if os.name == "nt" and handle.tell() == 0:
                return LockSnapshot(resolved, True, None, False)
            try:
                acquire_file_lock(handle, prepare=False)
            except LockUnavailableError:
                held = True
                # An active Windows lock makes byte zero unreadable.  Locks
                # created by this module keep metadata after that byte.
                handle.seek(1 if os.name == "nt" else 0)
                owner = handle.read().strip() or None
            else:
                held = False
                release_file_lock(handle)
                handle.seek(0)
                owner = handle.read().strip() or None
    except FileNotFoundError:
        return LockSnapshot(resolved, False, None, False)
    return LockSnapshot(resolved, True, owner, held)


def file_lock_is_held(path: Path) -> bool:
    """Return whether a path currently has an active advisory lock."""

    return inspect_file_lock(path).held
