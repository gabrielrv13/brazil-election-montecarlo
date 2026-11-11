"""Line-ending-independent SHA-256 for text files under git autocrlf.

The preservation baselines were recorded on a Windows checkout (CRLF), while
Linux checkouts of the same blobs have LF. A text file therefore matches if
its raw, LF-normalised or CRLF-normalised bytes have the recorded digest.
Content changes still fail; only line-ending conversions are tolerated.
Documentary copies marked ``-text`` keep their strict byte comparison.
"""

from __future__ import annotations

import hashlib


def digests_qualquer_eol(raw: bytes) -> set[str]:
    lf = raw.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    return {hashlib.sha256(v).hexdigest() for v in (raw, lf, crlf)}
