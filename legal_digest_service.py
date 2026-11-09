"""A small API that turns legal matter state into a scheduled subscriber digest."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

from infrai_client import InfraiError, infrai

@dataclass
class Matter:
    reference: str
    intake_complete: bool
    signed_document_url: str | None = None
    deadline: date | None = None


@dataclass
class DigestRequest:
    subscribers: list[str]
    matters: list[Matter]
    today: date


def digest_lines(matters: list[Matter], today: date) -> list[str]:
    """Keep signed delivery and deadlines visible, with incomplete intake first."""
    lines: list[str] = []
    for matter in matters:
        if not matter.intake_complete:
            lines.append(f"{matter.reference}: intake needs completion")
        if matter.signed_document_url:
            lines.append(f"{matter.reference}: signed document {matter.signed_document_url}")
        if matter.deadline and today <= matter.deadline <= today + timedelta(days=7):
            lines.append(f"{matter.reference}: deadline follow-up by {matter.deadline.isoformat()}")
    return lines


def send_scheduled_digest(request: DigestRequest) -> dict[str, int]:
    lines = digest_lines(request.matters, request.today)
    if not lines:
        return {"delivered": 0}
    messages = [
        {"to": subscriber, "subject": "Legal matter digest", "text": "\n".join(lines)}
        for subscriber in request.subscribers
    ]
    infrai.email.batch.send(messages=messages)
    return {"delivered": len(messages)}


def request_from_json(body: dict[str, object]) -> DigestRequest:
    matters = [
        Matter(
            reference=str(item["reference"]),
            intake_complete=bool(item["intake_complete"]),
            signed_document_url=item.get("signed_document_url"),
            deadline=date.fromisoformat(item["deadline"]) if item.get("deadline") else None,
        )
        for item in body["matters"]
    ]
    return DigestRequest(
        subscribers=[str(value) for value in body["subscribers"]],
        matters=matters,
        today=date.fromisoformat(str(body["today"])),
    )


class DigestHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/scheduled-legal-digest":
            self.send_error(404)
            return
        try:
            length = int(self.headers["Content-Length"])
            result = send_scheduled_digest(request_from_json(json.loads(self.rfile.read(length))))
            self.send_response(200)
        except (KeyError, TypeError, ValueError) as error:
            result = {"error": str(error)}
            self.send_response(400)
        except InfraiError as error:
            result = {"error": error.error}
            self.send_response(error.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())


if __name__ == "__main__":
    print("legal digest service listening on http://127.0.0.1:8000")
    HTTPServer(("127.0.0.1", 8000), DigestHandler).serve_forever()
