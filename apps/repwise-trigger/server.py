"""A page with one button, which runs `repwise update --apply --push`.

For the days the laptop was left closed before the gym. The button writes to a
Garmin account and the page is on the internet, so who may press it has to be
decided, and that is not done here: this listens on localhost alone, and the
oauth2-proxy beside it in the pod is the only way in.

The page can also log in to Garmin, for when the session repwise relies on has
run out somewhere a terminal is not to hand. The password is handed to Garmin
and kept nowhere, which is what repwise does with one typed at its own prompt.
"""

import json
import os
import signal
import subprocess
import sys
import threading
import urllib.request
from datetime import datetime
from datetime import timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer

import garminconnect
import jinja2
import yaml

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
CONFIG_URL = os.environ["CONFIG_URL"]
CONFIG_PATH = os.environ["REPWISE_CONFIG"]
COMMAND = ["repwise", "update", "--apply", "--push"]
TIMEOUT_SECONDS = 600

# Held for a run, and for each step of a login, so that neither meets the other
# halfway through writing the tokens.
running = threading.Lock()
last = {"finished": None, "result": "Not run since the pod started", "output": ""}
# A login that Garmin wants an MFA code for, and where its tokens are to go.
pending = None

# Loaded as the process starts, so that an image built without the page fails
# there and not at the first visit. Nothing is put into the page yet, and
# whatever comes to be is escaped.
PAGE = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__), "templates")
    ),
    autoescape=True,
).get_template("index.html")


def fetch_config() -> dict:
    """Download workouts.yaml to where repwise reads it, and return what it says.

    On every run, because repwise reshapes the Garmin workouts to match the
    file it is given: a copy gone stale here would undo an edit made since.
    """
    request = urllib.request.Request(
        CONFIG_URL,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.raw+json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read()
    except OSError as exc:
        raise RuntimeError(f"Could not download {CONFIG_URL}: {exc}") from exc

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "wb") as fh:
        fh.write(text)
    return yaml.safe_load(text)


def run() -> None:
    """One run, whose outcome is kept for the page and printed for the pod's log."""
    try:
        # repwise builds a workout that has no id and writes the id Garmin
        # issued back into the file. This copy is replaced by the next download,
        # so the id would be lost with it and the next run would build the
        # workout again.
        new = [
            workout["key"]
            for workout in fetch_config()["workouts"]
            if not workout.get("garmin_workout_id")
        ]
        if new:
            raise RuntimeError(
                f"{', '.join(new)}: no garmin_workout_id yet. Run repwise where "
                "workouts.yaml is edited, so that the id is written into the file, "
                "and push it."
            )
        # Without a terminal repwise explains a missing Garmin session and
        # exits, where it would otherwise wait on a login prompt.
        done = subprocess.run(
            COMMAND,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        result = "Done" if done.returncode == 0 else f"repwise exited {done.returncode}"
        output = done.stdout
    except Exception as exc:  # whatever it was, the page is where it gets read
        result, output = "Failed", f"{type(exc).__name__}: {exc}"
    last.update(
        finished=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        result=result,
        output=output,
    )
    running.release()
    print(f"{result}\n{output}", flush=True)


def login(email: str, password: str) -> bool:
    """Start a Garmin login. True when Garmin wants an MFA code to finish it."""
    global pending
    # Where repwise will look for the tokens is workouts.yaml's to say. Found
    # and made before Garmin is asked for anything: a login is the request
    # Garmin rate-limits hardest, and one that succeeded with nowhere to keep
    # its tokens would be a login thrown away.
    garmin = fetch_config().get("settings", {}).get("garmin", {})
    store = os.path.expanduser(garmin.get("token_store") or "~/.config/repwise")
    os.makedirs(store, mode=0o700, exist_ok=True)

    api = garminconnect.Garmin(email, password, return_on_mfa=True)
    wants_code, _ = api.login()
    # Kept by the library for the lifetime of the object, which a login waiting
    # on its code would otherwise make as long as the pod's.
    api.password = None
    if wants_code:
        pending = (api, store)
        return True
    api.client.dump(store)
    return False


def finish_login(code: str) -> None:
    """Finish the login that is waiting with its MFA code, and keep the tokens."""
    global pending
    if pending is None:
        raise RuntimeError("No login is waiting for a code. Log in again.")
    api, store = pending
    # A wrong code raises here and leaves the login waiting, to be tried again.
    api.resume_login(None, code)
    api.client.dump(store)
    pending = None


class Handler(BaseHTTPRequestHandler):
    def reply(
        self, status: HTTPStatus, body: bytes = b"", content_type: str = "text/plain"
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            self.reply(
                HTTPStatus.OK, PAGE.render().encode(), "text/html; charset=utf-8"
            )
        elif self.path != "/status":
            self.reply(HTTPStatus.NOT_FOUND)
        else:
            status = {"running": running.locked(), **last}
            self.reply(HTTPStatus.OK, json.dumps(status).encode(), "application/json")

    def do_POST(self) -> None:
        if self.path not in ("/run", "/login", "/mfa"):
            self.reply(HTTPStatus.NOT_FOUND)
        elif not running.acquire(blocking=False):
            self.reply(HTTPStatus.CONFLICT, b"Busy with a run or a login. Try again.")
        elif self.path == "/run":
            # Not a daemon, which it would inherit from the request's thread: a
            # run in progress is finished before the process exits.
            threading.Thread(target=run, daemon=False).start()
            self.reply(HTTPStatus.ACCEPTED)
        else:
            self.log_in()

    def log_in(self) -> None:
        """One step of a Garmin login, answered with whether a code is wanted.

        The form is read and passed on, and never printed: what reaches the
        pod's log is which step it was and how it ended.
        """
        try:
            form = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/login":
                wants_code = login(form["email"], form["password"])
            else:
                finish_login(form["code"])
                wants_code = False
        # 400 whatever it was, and not 401 for a wrong password: the page takes
        # 401 to mean its own sign-in has run out.
        except Exception as exc:
            print(f"Garmin {self.path[1:]} failed: {type(exc).__name__}", flush=True)
            self.reply(HTTPStatus.BAD_REQUEST, f"{type(exc).__name__}: {exc}".encode())
        else:
            print(
                f"Garmin {self.path[1:]}: {'code wanted' if wants_code else 'logged in'}",
                flush=True,
            )
            self.reply(
                HTTPStatus.OK,
                json.dumps({"mfa": wants_code}).encode(),
                "application/json",
            )
        finally:
            running.release()


if __name__ == "__main__":
    # As PID 1 a process gets no default SIGTERM handling, so without this every
    # rollout would wait out the grace period.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
