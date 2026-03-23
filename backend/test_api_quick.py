"""Quick live test of the /api/analyze endpoint."""
import json, urllib.request, urllib.error

BOUNDARY = "TESTBND"
CRLF = b"\r\n"

def field(name, value):
    return (
        b"--" + BOUNDARY.encode() + CRLF +
        b'Content-Disposition: form-data; name="' + name.encode() + b'"' + CRLF +
        CRLF +
        value.encode() + CRLF
    )

body = field("prompt", "simple web app 10 users") + field("region", "us-east-1") + b"--" + BOUNDARY.encode() + b"--" + CRLF

req = urllib.request.Request("http://localhost:8000/api/analyze", data=body, method="POST")
req.add_header("Content-Type", "multipart/form-data; boundary=" + BOUNDARY)
req.add_header("Content-Length", str(len(body)))

try:
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read())
    print("SUCCESS, session_id:", data.get("session_id"))
except urllib.error.HTTPError as e:
    print("HTTP ERROR", e.code)
    raw = e.read().decode()
    print(raw)
except Exception as ex:
    print("EXCEPTION:", type(ex).__name__, ex)
