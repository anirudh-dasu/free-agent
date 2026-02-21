"""
Sandboxed Python code execution via subprocess.
The agent can run arbitrary Python to compute, analyse data, or generate output.
"""
import subprocess
import sys


TIMEOUT_SECONDS = 10
MAX_OUTPUT_CHARS = 4000


def run_python(code: str) -> str:
    """
    Execute Python code in a subprocess and return stdout + stderr.
    Raises nothing — all errors are captured and returned as text.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr

        if not output:
            output = "(no output)"

        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + f"\n\n[... output truncated at {MAX_OUTPUT_CHARS} chars ...]"

        return output

    except subprocess.TimeoutExpired:
        return f"Error: code execution timed out after {TIMEOUT_SECONDS} seconds."
    except Exception as e:
        return f"Error running code: {e}"
