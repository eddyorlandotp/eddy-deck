"""One receiver may recover a data directory at a time, including headless use."""
import errno,msvcrt
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def receiver_lease(data):
    path=Path(data)/'receiver.lock';path.parent.mkdir(parents=True,exist_ok=True)
    # Windows releases a byte-range lock if a process exits unexpectedly.
    # Keep the file; deleting/recreating it would create two independent locks.
    with path.open('a+b') as stream:
        if stream.seek(0,2)==0:stream.write(b'1');stream.flush()
        stream.seek(0)
        try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError as exc:
            if exc.errno not in (errno.EACCES,errno.EDEADLK):raise
            yield False;return
        try:yield True
        finally:
            stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
