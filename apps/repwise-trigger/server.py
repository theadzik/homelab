"""A page with one button, which runs `repwise update --apply --push`.

For the days the laptop was left closed before the gym. The button writes to a
Garmin account and the page is on the internet, so who may press it has to be
decided, and that is not done here: this listens on localhost alone, and the
oauth2-proxy beside it in the pod is the only way in.
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

import yaml

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
CONFIG_URL = os.environ["CONFIG_URL"]
CONFIG_PATH = os.environ["REPWISE_CONFIG"]
COMMAND = ["repwise", "update", "--apply", "--push"]
TIMEOUT_SECONDS = 600

running = threading.Lock()
last = {"finished": None, "result": "Not run since the pod started", "output": ""}

PAGE = b"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>repwise</title>
<style>
  body { font: 16px system-ui, sans-serif; margin: 1rem; }
  button { font: inherit; font-size: 1.5rem; width: 100%; padding: 1.5rem; }
  pre { font-size: 0.75rem; overflow-x: auto; }
</style>
<button id="run">Update</button>
<p id="state"></p>
<pre id="output"></pre>
<script>
  const button = document.getElementById("run");
  const state = document.getElementById("state");
  const output = document.getElementById("output");

  // oauth2-proxy answers a request that asks for JSON with 401 once the session
  // has run out, where it would redirect a page. Loading the page again is what
  // takes that redirect, to the sign-in and back.
  async function call(method, path) {
    const response = await fetch(path, {method, headers: {Accept: "application/json"}});
    if (response.status === 401) {
      location.reload();
      await new Promise(() => {});
    }
    return response;
  }

  async function refresh() {
    try {
      const status = await (await call("GET", "status")).json();
      const when = status.finished ? " - " + new Date(status.finished).toLocaleString() : "";
      button.disabled = status.running;
      state.textContent = status.running ? "Running..." : status.result + when;
      output.textContent = status.running ? "" : status.output;
      if (status.running) setTimeout(refresh, 2000);
    } catch (error) {
      state.textContent = error.message + " Reload to try again.";
    }
  }

  button.onclick = async () => {
    button.disabled = true;
    try {
      await call("POST", "run");
    } finally {
      await refresh();
    }
  };
  refresh();
</script>
"""


def fetch_config() -> None:
    """Download workouts.yaml to where repwise reads it.

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

    # repwise builds a workout that has no id and writes the id Garmin issued
    # back into the file. This copy is replaced by the next download, so the id
    # would be lost with it and the next run would build the workout again.
    new = [
        workout["key"]
        for workout in yaml.safe_load(text)["workouts"]
        if not workout.get("garmin_workout_id")
    ]
    if new:
        raise RuntimeError(
            f"{', '.join(new)}: no garmin_workout_id yet. Run repwise where workouts.yaml is "
            "edited, so that the id is written into the file, and push it."
        )

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "wb") as fh:
        fh.write(text)


def run() -> None:
    """One run, whose outcome is kept for the page and printed for the pod's log."""
    try:
        fetch_config()
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
            self.reply(HTTPStatus.OK, PAGE, "text/html; charset=utf-8")
        elif self.path != "/status":
            self.reply(HTTPStatus.NOT_FOUND)
        else:
            status = {"running": running.locked(), **last}
            self.reply(HTTPStatus.OK, json.dumps(status).encode(), "application/json")

    def do_POST(self) -> None:
        if self.path != "/run":
            self.reply(HTTPStatus.NOT_FOUND)
        elif not running.acquire(blocking=False):
            self.reply(HTTPStatus.CONFLICT)
        else:
            # Not a daemon, which it would inherit from the request's thread: a
            # run in progress is finished before the process exits.
            threading.Thread(target=run, daemon=False).start()
            self.reply(HTTPStatus.ACCEPTED)


if __name__ == "__main__":
    # As PID 1 a process gets no default SIGTERM handling, so without this every
    # rollout would wait out the grace period.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
