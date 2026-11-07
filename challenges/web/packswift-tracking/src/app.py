from __future__ import annotations

import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import skin

HERE = Path(__file__).resolve().parent
PROXY_SETUP = HERE / "files" / "proxy-setup.html"
FONT_DIR = HERE / "static" / "fonts"

FONT_FILES = frozenset(
    {
        "archivo-var.woff2",
        "overpass-mono-var.woff2",
        "courier-prime-400.woff2",
        "courier-prime-700.woff2",
        "b612-mono-700.woff2",
    }
)

FLAG = os.environ.get("FLAG", "").strip()
if not FLAG:
    print("tracking: FLAG is not set", file=sys.stderr)
    raise SystemExit(1)

DEPLOY_LOG_ENTRIES = (
    {
        "rev": "C",
        "date": "14 November",
        "time": "10:05",
        "actor": "Edge",
        "text": (
            "The edge now answers a request that carries two length headers and "
            "never passes it to the application. The edge reads a chunked body to its "
            "end before it passes anything on. Nobody touched the application."
        ),
        "tail": "It still prefers a length header and does not read chunking.",
    },
    {
        "rev": "B",
        "date": "14 November",
        "time": "09:40",
        "actor": "Edge",
        "text": (
            "The edge answers any address starting with <code>/internal/</code> with "
            "a 403. It also removes the <code>X-PackSwift-Role</code> header from "
            "everything it passes on, so a role cannot arrive from outside."
        ),
        "tail": "",
    },
    {
        "rev": "A",
        "date": "13 November",
        "time": "16:20",
        "actor": "Support",
        "text": (
            "The onboarding page for the request tool is at "
            '<a href="/proxy-setup">/proxy-setup</a>. New starters should read it '
            "before their first shift."
        ),
        "tail": "",
    },
)

HOME_NOTES = (
    skin.note(
        "MARGIN NOTE 1",
        "The edge owns the front door. Every customer request stops there first.",
    )
    + skin.note(
        "MARGIN NOTE 2",
        "The application is the second reader. Last quarter's work did not touch "
        "it.",
        "blue",
    )
)

LOG_NOTES = (
    skin.note(
        "MARGIN NOTE 3",
        "Two entries, one date. The edge changed in the morning. The application "
        "did not.",
    )
    + skin.note(
        "REVISION CLOUD",
        "The circled sentence is the one to read twice.",
        "red",
    )
)


def home_page(code: str = "PS-1042", submitted: bool = False) -> str:
    body = (
        '<p class="a-copy">Enter the code from your receipt to see the latest scan.</p>'
        + skin.track_form(code)
        + (skin.result(code) if submitted else "")
        + skin.figure()
    )
    return skin.page(
        title="Tracking · PackSwift",
        sheet_no="01",
        section="SHEET 01 &middot; CUSTOMER SIDE",
        heading="Tracking index",
        body=body,
        notes=HOME_NOTES,
        active="home",
    )


def deploy_log_page() -> str:
    rows = []
    for entry in DEPLOY_LOG_ENTRIES:
        tail = (
            f'<p class="a-cloud">{entry["tail"]}</p>' if entry["tail"] else ""
        )
        rows.append(
            '<article class="a-rev-row">'
            f'<div class="a-rev-letter">{entry["rev"]}</div>'
            '<div class="a-rev-meta">'
            f'<p>{entry["date"]}</p>'
            f'<p class="a-mono">{entry["time"]}</p>'
            f'<p class="a-rev-actor">{entry["actor"]}</p>'
            "</div>"
            f'<div class="a-rev-text"><p>{entry["text"]}</p>{tail}</div>'
            "</article>"
        )
    body = (
        '<div class="a-revisions">'
        + "".join(rows)
        + "</div>"
        + '<p class="a-log-foot">REVISION BLOCK &middot; KEPT WITH THE DRAWING SET '
        "&middot; PACKSWIFT INTERNAL</p>"
    )
    return skin.page(
        title="Deploy log · PackSwift Tracking",
        sheet_no="02",
        section="SHEET 02 &middot; CHANGE CONTROL",
        heading="Deploy log",
        lede="Changes to the tracking tier. Newest first.",
        body=body,
        notes=LOG_NOTES,
        active="log",
    )


def role_page() -> str:
    body = (
        skin.confirm(FLAG)
        + '<p class="a-copy">This address is for the dispatcher role. A request '
        "that does not carry that role is refused.</p>"
    )
    return skin.page(
        title="Dispatcher role · PackSwift",
        sheet_no="03",
        section="SHEET 03 &middot; RESTRICTED",
        heading="Dispatcher role",
        body=body,
        notes=skin.note(
            "MARGIN NOTE 4",
            "The edge strips this header from everything it passes on. The "
            "application still read it.",
            "red",
        ),
        active=None,
    )


def not_found_page(path: str) -> str:
    return skin.page(
        title="Not found · PackSwift Tracking",
        sheet_no="07",
        body=skin.exception(
            kicker="SHEET NOT ISSUED &middot; APPLICATION 404",
            heading="Not found",
            path=f"GET {path}",
            paragraph="There is no page at this address.",
            stamp_label="APP 404",
            stamp_sub="NOT ISSUED",
            link=False,
        )
        + '<p class="a-exlink"><a href="/">Back to tracking</a></p>',
        notes=skin.note(
            "MARGIN NOTE 9",
            "If it is not in this set, it was never drawn.",
        ),
        active=None,
    )


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PackSwiftTracking/1.0"

    def log_message(self, _format: str, *args) -> None:
        pass

    def _send(
        self,
        status: int,
        body: str,
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _font(self, name: str) -> None:
        if name not in FONT_FILES:
            self._send(404, not_found_page(f"/fonts/{name}"))
            return
        data = (FONT_DIR / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "font/woff2")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def _read_tracking_code(self, body: bytes) -> str:
        try:
            fields = urllib.parse.parse_qs(
                body.decode("utf-8", "replace"), max_num_fields=20
            )
            candidate = (fields.get("code") or [""])[0].strip()
        except (ValueError, UnicodeError):
            candidate = ""
        return candidate[:64] or "PS-1042"

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/_health":
            self._send(200, "ok", "text/plain; charset=utf-8")
        elif path == "/":
            self._send(200, home_page())
        elif path == "/deploy-log":
            self._send(200, deploy_log_page())
        elif path == "/proxy-setup":
            try:
                page = PROXY_SETUP.read_text(encoding="utf-8")
            except OSError:
                self._send(404, not_found_page(path))
                return
            self._send(200, page)
        elif path == "/internal/role":
            self._role()
        elif path.startswith("/fonts/"):
            self._font(path[len("/fonts/") :])
        else:
            self._send(404, not_found_page(path))

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/track":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            self._send(200, home_page(self._read_tracking_code(body), submitted=True))
        else:
            self._send(404, not_found_page(path))

    def _role(self) -> None:
        if self.headers.get("X-PackSwift-Role") == "dispatcher":
            self._send(200, role_page())
        else:
            self._send(
                403,
                skin.page(
                    title="Not available · PackSwift",
                    sheet_no="03",
                    body=skin.exception(
                        kicker="EXCEPTION &middot; ANSWERED BY THE APPLICATION",
                        heading="Not available",
                        path="GET /internal/role",
                        paragraph="This address is for the dispatcher role. The "
                        "request did not carry that role.",
                        stamp_label="APP 403",
                        stamp_sub="NO ROLE",
                        link=False,
                    ),
                    notes=skin.note(
                        "MARGIN NOTE 4",
                        "The application read the role header and refused this "
                        "request.",
                    ),
                    active=None,
                ),
            )


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    with Server(("127.0.0.1", 9090), Handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
