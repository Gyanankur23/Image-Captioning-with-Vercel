import os
import json
import base64
from http.server import BaseHTTPRequestHandler

from google import genai
from google.genai import types

# Client reads the API key from the environment (set GEMINI_API_KEY in
# Vercel's Project Settings -> Environment Variables).
_api_key = os.environ.get("GEMINI_API_KEY")
_client = genai.Client(api_key=_api_key) if _api_key else None

MODEL_NAME = "gemini-2.0-flash"


class handler(BaseHTTPRequestHandler):
    """Vercel Python runtime expects a BaseHTTPRequestHandler subclass
    named `handler` in api/*.py — that's the actual contract, unlike the
    AWS-Lambda-style dict return this file used before."""

    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        # Friendly response if someone hits the endpoint directly in a browser.
        self._send_json(405, {"error": "Use POST with a JSON body: {\"image\": \"<data URL or base64>\"}"})

    def do_POST(self):
        try:
            if _client is None:
                self._send_json(
                    500,
                    {"error": "GEMINI_API_KEY is not set. Add it in Vercel Project Settings -> Environment Variables and redeploy."},
                )
                return

            content_length = int(self.headers.get("Content-Length", 0) or 0)
            raw_body = self.rfile.read(content_length) if content_length else b""

            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON body"})
                return

            image_data = data.get("image")
            if not image_data:
                self._send_json(400, {"error": "No image provided"})
                return

            # Support both raw base64 and data: URLs, and detect the real mime type
            # instead of hardcoding image/jpeg.
            mime_type = "image/jpeg"
            if image_data.startswith("data:"):
                header, _, encoded = image_data.partition(",")
                image_data = encoded
                if ";" in header:
                    parsed_mime = header.split(":", 1)[1].split(";", 1)[0]
                    if parsed_mime:
                        mime_type = parsed_mime

            try:
                image_bytes = base64.b64decode(image_data)
            except Exception:
                self._send_json(400, {"error": "Invalid base64 image data"})
                return

            response = _client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    "Write exactly one short, single-line caption (max 20 words) "
                    "describing this image. Respond with only the caption text, "
                    "no preamble, no quotes, no extra lines.",
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ],
            )

            caption_text = (response.text or "").strip()
            # Guard against the model ever returning multiple lines.
            caption = caption_text.splitlines()[0].strip() if caption_text else "No caption generated."

            self._send_json(200, {"caption": caption})

        except Exception as e:
            self._send_json(500, {"error": str(e)})
