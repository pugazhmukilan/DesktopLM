import json
import os
import subprocess
from pathlib import Path
from typing import Callable, List, Dict, Any

# ---------------------------------------------------------------------------
# Generic MCP command tool
# ---------------------------------------------------------------------------
class MCPCommandTool:
    """Callable wrapper for an external MCP command defined in the JSON config.

    The tool name is the key from the config (e.g. "documentation").
    When called, it runs the configured command + args via ``subprocess`` and
    returns the captured stdout (or an error string).  All environment variables
    are inherited from the current process, and the working directory is the
    directory of the command (if ``--directory`` is present it is used).
    """

    def __init__(self, name: str, command: str, args: List[str]):
        self.name = name
        self.command = command
        self.args = args
        # Human‑readable description used by the LLM tool registry
        self.description = f"Run the '{name}' MCP command via `{command}` with arguments {args}."

    def __call__(self, *extra_args: str) -> str:
        """Execute the command.

        ``extra_args`` are appended to the configured argument list – this lets the
        LLM pass a dynamic payload (e.g. a file path or a prompt) without needing a
        separate wrapper for each tool.
        """
        cmd = [self.command] + self.args + list(extra_args)
        import shutil
        executable = shutil.which(cmd[0])
        if not executable:
            return f"❌ MCP tool error: The command '{cmd[0]}' is not installed or not in the system PATH."
        cmd[0] = executable

        try:
            # ``subprocess.run`` captures stdout/stderr, raises on non‑zero exit
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self._determine_cwd(),
                timeout=30,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"❌ MCP command '{self.name}' failed (exit {e.returncode}): {e.stderr.strip()}"
        except Exception as exc:
            return f"❌ MCP command '{self.name}' error: {exc}"

    def _determine_cwd(self) -> str:
        """If the argument list contains ``--directory <path>`` use that as cwd.
        This mirrors the Claude Desktop config format.
        """
        if "--directory" in self.args:
            idx = self.args.index("--directory")
            if idx + 1 < len(self.args):
                return os.path.abspath(self.args[idx + 1])
        return os.getcwd()

    # The LLM expects a ``name`` attribute for tool discovery
    @property
    def __name__(self) -> str:  # pragma: no cover – used by DesktopLM loader
        return self.name

# ---------------------------------------------------------------------------
# Loader that reads the JSON config and creates tool instances
# ---------------------------------------------------------------------------
def load_mcp_tools(config_path: str | os.PathLike = None) -> List[Callable[[str], str]]:
    """Read ``tools/mcp_config.json`` (or a custom path) and return a list of
    ``MCPCommandTool`` callables ready to be registered via ``tools/registry.py``.
    """
    if config_path is None:
        # Default location next to this module
        config_path = Path(__file__).with_name("mcp_config.json")
    else:
        config_path = Path(config_path)

    if not config_path.is_file():
        # Silently return an empty list – the application can still run.
        return []

    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        # If the JSON is malformed we expose the error as a dummy tool so the LLM
        # can surface the problem.
        def broken_tool(_: str) -> str:
            return f"❌ Failed to load MCP config ({config_path}): {exc}"
        broken_tool.name = "mcp_config_error"
        broken_tool.__name__ = "mcp_config_error"
        return [broken_tool]

    tools: List[Callable[[str], str]] = []
    for name, spec in cfg.get("mcpServers", {}).items():
        command = spec.get("command")
        args = spec.get("args", [])
        if not command:
            continue
        tools.append(MCPCommandTool(name=name, command=command, args=args))
    return tools
