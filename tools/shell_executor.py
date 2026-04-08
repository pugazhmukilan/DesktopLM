import logging
import subprocess
from typing import Annotated

from langchain_core.tools import tool
from agent.permissions import request_approval

logger = logging.getLogger("desktoplm.tools.shell")

@tool
def run_cli_command(
    command: Annotated[str, "The exact terminal command to execute."],
    timeout: Annotated[int, "Timeout in seconds (default 60)."] = 60
) -> str:
    """Run a terminal command (shell script) on the user's machine. 
    Use this to execute software builds, test files, run git commands, or fulfill `.md` skill steps.
    """
    # Enforce permission check before executing any command.
    if not request_approval("run_cli_command", {"command": command}):
        return "Skipped (denied by user)"
        
    try:
        # We specify powershell.exe since the user is on Windows.
        result = subprocess.run(
            ["powershell.exe", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        
        output_str = f"Exit code: {result.returncode}\n"
        if out:
            output_str += f"STDOUT:\n{out[:4000]}\n"
        if err:
            output_str += f"STDERR:\n{err[:4000]}\n"
            
        return output_str
    except subprocess.TimeoutExpired:
        return f"Command execution timed out after {timeout} seconds."
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return f"Error executing command: {e}"
