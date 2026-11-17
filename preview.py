"""Run the same routes locally with a small SQLite database."""

from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

from src.app import handle, json_response


DATABASE = Path(__file__).with_name(".preview.sqlite3")


class LocalLinks:
    def __init__(self):
        with closing(sqlite3.connect(DATABASE)) as database, database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS links "
                "(code TEXT PRIMARY KEY, destination TEXT NOT NULL, visits INTEGER NOT NULL)"
            )

    def create(self, code, destination):
        with closing(sqlite3.connect(DATABASE)) as database, database:
            result = database.execute(
                "INSERT OR IGNORE INTO links VALUES (?, ?, 0)", (code, destination)
            )
            return result.rowcount == 1

    def visit(self, code):
        with closing(sqlite3.connect(DATABASE)) as database, database:
            row = database.execute(
                "UPDATE links SET visits = visits + 1 WHERE code = ? RETURNING destination",
                (code,),
            ).fetchone()
            return row[0] if row else None

    def count(self, code):
        with closing(sqlite3.connect(DATABASE)) as database:
            row = database.execute("SELECT visits FROM links WHERE code = ?", (code,)).fetchone()
            return row[0] if row else None


class PreviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.reply(handle("GET", urlsplit(self.path).path, "", self.server.store))

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.reply(json_response(400, error="Invalid content length."))
            return
        if not 0 <= length <= 8192:
            self.reply(json_response(413, error="The request is too large."))
            return
        self.reply(handle("POST", urlsplit(self.path).path, self.rfile.read(length), self.server.store))

    def reply(self, result):
        self.send_response(result["statusCode"])
        for name, value in result["headers"].items():
            self.send_header(name, value)
        body = result["body"].encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 8765), PreviewHandler) as server:
        server.store = LocalLinks()
        print("Open http://127.0.0.1:8765 in your browser. Press Ctrl+C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
