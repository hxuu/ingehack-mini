"""NetCheck - intentionally vulnerable network diagnostic tool.

Concept: OS command injection. The host field is pasted into a string that is
handed to a shell, so the player can append another command with `;` and read
/flag.txt.

See ../solution/SOLUTION.md for the intended solution and the fix.
"""

import subprocess

from flask import Flask, render_template, request

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/ping")
def ping():
    host = request.form.get("host", "").strip()

    if not host:
        return render_template(
            "index.html", host=host, output="Enter a hostname or IP address."
        )

    try:
        # VULN: user input is concatenated into a shell command string and run
        # with shell=True, so `;`, `&&`, `|` or `$(...)` start new commands.
        result = subprocess.run(
            "ping -c 2 " + host,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired:
        output = "Request timed out after 10 seconds."

    return render_template("index.html", host=host, output=output)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
