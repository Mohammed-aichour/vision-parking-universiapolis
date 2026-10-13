"""Static server with byte ranges so browser video seeking works."""

import os
import re
from http.server import SimpleHTTPRequestHandler


class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
    _byte_range: tuple[int, int] | None = None

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        self._byte_range = None
        request_range = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not request_range or not os.path.isfile(path):
            return super().send_head()
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", request_range.strip())
        if not match or not any(match.groups()):
            self.send_error(416, "Portion demandée invalide")
            return None
        size = os.path.getsize(path)
        first, last = match.groups()
        if first:
            start = int(first)
            end = int(last) if last else size - 1
        else:
            suffix = int(last)
            start, end = max(0, size - suffix), size - 1
        if start >= size or start > end or end >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        source = open(path, "rb")
        self._byte_range = (start, end)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        return source

    def copyfile(self, source, outputfile):
        if self._byte_range is None:
            return super().copyfile(source, outputfile)
        start, end = self._byte_range
        source.seek(start)
        remaining = end - start + 1
        while remaining:
            chunk = source.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)
