import json
import mimetypes
import os
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import (
    parse_qs,
    unquote,
    urlsplit,
)


ARTIFACTS_BASE = Path(
    "/opt/uqa/artifacts/browser"
).resolve()

TOKENS_FILE = Path(
    "/etc/uqa-artifacts/tokens.json"
)

BIND = os.getenv(
    "UQA_ARTIFACT_BIND",
    "192.168.50.72",
)

PORT = int(
    os.getenv(
        "UQA_ARTIFACT_PORT",
        "8765",
    )
)


def load_tokens():
    data = json.loads(
        TOKENS_FILE.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, dict):
        raise RuntimeError(
            "tokens.json must contain an object"
        )

    return data


class ArtifactHandler(
    BaseHTTPRequestHandler
):
    server_version = "UQAArtifactServer/1.0"

    def log_message(
        self,
        fmt,
        *args,
    ):
        # Не пишем URL/token в journal.
        return

    def _send_error(
        self,
        code,
        message,
    ):
        body = (
            message + "\n"
        ).encode("utf-8")

        self.send_response(code)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )
        self.end_headers()

        if self.command != "HEAD":
            self.wfile.write(body)

    def _resolve_target(self):
        parsed = urlsplit(
            self.path
        )

        parts = [
            unquote(part)
            for part
            in parsed.path.split("/")
            if part
        ]

        # /artifact/<token>/<relative/path>
        if (
            len(parts) < 3
            or parts[0] != "artifact"
        ):
            return None, None, 404

        token = parts[1]

        tokens = load_tokens()

        username = tokens.get(
            token
        )

        if not username:
            return None, None, 403

        user_root = (
            ARTIFACTS_BASE
            / username
        ).resolve()

        relative = Path(
            *parts[2:]
        )

        target = (
            user_root
            / relative
        ).resolve()

        # Не позволяем ../ или symlink escape.
        if not target.is_relative_to(
            user_root
        ):
            return None, None, 403

        if not target.is_file():
            return None, None, 404

        return (
            target,
            parsed,
            200,
        )

    def _serve(self):
        (
            target,
            parsed,
            status,
        ) = self._resolve_target()

        if status == 403:
            return self._send_error(
                403,
                "Forbidden",
            )

        if status != 200:
            return self._send_error(
                404,
                "Not found",
            )

        try:
            size = target.stat().st_size
        except OSError:
            return self._send_error(
                404,
                "Not found",
            )

        content_type = (
            mimetypes.guess_type(
                target.name
            )[0]
            or "application/octet-stream"
        )

        query = parse_qs(
            parsed.query
        )

        download = (
            query.get(
                "download",
                [""],
            )[0]
            in (
                "1",
                "true",
                "yes",
            )
        )

        self.send_response(200)

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(size),
        )

        self.send_header(
            "Cache-Control",
            "private, max-age=60",
        )

        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )

        disposition = (
            "attachment"
            if download
            else "inline"
        )

        self.send_header(
            "Content-Disposition",
            (
                f'{disposition}; '
                f'filename="{target.name}"'
            ),
        )

        self.end_headers()

        if self.command == "HEAD":
            return

        try:
            with target.open("rb") as fh:
                while True:
                    chunk = fh.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    self.wfile.write(
                        chunk
                    )
        except (
            BrokenPipeError,
            ConnectionResetError,
        ):
            pass

    def do_GET(self):
        self._serve()

    def do_HEAD(self):
        self._serve()


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        (
            BIND,
            PORT,
        ),
        ArtifactHandler,
    )

    print(
        f"UQA Artifact Server "
        f"listening on "
        f"http://{BIND}:{PORT}",
        flush=True,
    )

    server.serve_forever()
