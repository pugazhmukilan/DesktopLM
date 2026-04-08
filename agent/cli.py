"""CLI entry for the `desktoplm` command: doctor, demos, chat, and repl."""

from __future__ import annotations

import sys
import pyfiglet

from agent.run_logging import configure_logging

# ANSI helpers (ASCII-safe for Windows cp1252)
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_RESET = "\033[0m"

_DEFAULT_CHAT = (
    "Summarize what you know about my schedule and preferences using memory tools if needed."
)

def create_banner():
    title = pyfiglet.figlet_format("DesktopLM", font="slant")
    version = "v0.2.0"
    tagline = "Local-first AI assistant with memory"
    
    colored_title = f"{_CYAN}{_BOLD}{title}{_RESET}"
    colored_version = f"{_YELLOW}{version}{_RESET}"
    colored_tagline = f"{_GREEN}{tagline}{_RESET}"
    
    banner = f"\n{colored_title}\n"
    banner += f"{' ' * (len(title.splitlines()[-1]) - len(version))}{colored_version}\n"
    banner += f"{' ' * ((len(title.splitlines()[-1]) - len(tagline)) // 2)}{colored_tagline}\n"
    banner += f"{_BOLD}+{'=' * (len(title.splitlines()[-1]))}+{_RESET}\n"
    
    return banner

_BANNER = create_banner()


def _usage_text() -> str:
    return f"""{_BANNER}
{_BOLD}Commands:{_RESET}
  desktoplm repl              Interactive chat (keeps context until exit)
  desktoplm doctor            Check data dir, Ollama, MongoDB, cloud keys
  desktoplm demo-memory       Memory extract + DB routing demo
  desktoplm chat <message>    Single message, then exit
  desktoplm <message>         Same as chat (shorthand)
  desktoplm select-model      Interactive model picker

{_BOLD}Examples:{_RESET}
  desktoplm repl
  desktoplm "What meetings do I have?"
  desktoplm chat hello
  desktoplm doctor

{_BOLD}REPL Commands:{_RESET}
  :switch    Change model (local <-> cloud) at runtime
  :model     Show current model info
  :tools     List loaded tools (built-in + MCP)
  :trust     Trust a tool for the session (skip approval)
  :help      Show commands
  :quit      Exit

{_BOLD}Options:{_RESET}
  -q, --quiet    Quieter console (errors only)
  --yes, -y      Auto-approve all tool actions (skip permission prompts)

Note: Each `desktoplm "..."` is a new process -- use `repl` for continuity.
Logs: <DESKTOPLM_DATA_DIR>/logs/desktoplm.log
"""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    quiet = False
    auto_yes = False
    filtered: list[str] = []
    for a in argv:
        if a in ("-q", "--quiet"):
            quiet = True
        elif a in ("--yes", "-y"):
            auto_yes = True
        else:
            filtered.append(a)
    argv = filtered

    configure_logging(quiet=quiet)

    # Apply auto-approve
    if auto_yes:
        from agent.permissions import set_auto_approve
        set_auto_approve(True)

    # No args (e.g. double-click on exe) -> launch REPL directly
    if not argv:
        print(_BANNER)
        try:
            from agent.pipeline import ChatPipeline
            return ChatPipeline().run_repl()
        except KeyboardInterrupt:
            print(f"\n{_DIM}Bye.{_RESET}")
            return 0
        except Exception as e:
            print(f"{_RED}Error:{_RESET} {e}", file=sys.stderr)
            input(f"\n{_DIM}Press Enter to close...{_RESET}")
            return 1

    # ---- commands ----

    if argv[0] in ("--doctor", "doctor"):
        from agent.doctor import run_doctor
        return run_doctor()

    if argv[0] == "demo-memory":
        from agent.demos import run_memory_write_demo
        return run_memory_write_demo()

    if argv[0] == "select-model":
        from LLMS.model_selector import select_model_interactive
        result = select_model_interactive()
        print(f"\n  {_GREEN}[ok]{_RESET} Selected: {_CYAN}{result['model']}{_RESET} ({result['mode']}/{result['provider']})")
        return 0

    if argv[0] in ("repl", "i", "interactive"):
        print(_BANNER)
        try:
            from agent.pipeline import ChatPipeline
            return ChatPipeline().run_repl()
        except KeyboardInterrupt:
            print(f"\n{_DIM}Bye.{_RESET}")
            return 0
        except Exception as e:
            print(f"{_RED}Error:{_RESET} {e}", file=sys.stderr)
            return 1

    if argv[0] in ("help", "-h", "--help"):
        print(_usage_text())
        return 0

    # ---- chat mode ----
    if argv[0] == "chat":
        text = " ".join(argv[1:]).strip()
    else:
        text = " ".join(argv).strip()

    if not text:
        if sys.stdin.isatty():
            print(f"{_DIM}No message given. Starting interactive session...{_RESET}\n")
            print(_BANNER)
            try:
                from agent.pipeline import ChatPipeline
                return ChatPipeline().run_repl()
            except KeyboardInterrupt:
                print(f"\n{_DIM}Bye.{_RESET}")
                return 0
            except Exception as e:
                print(f"{_RED}Error:{_RESET} {e}", file=sys.stderr)
                return 1
        text = _DEFAULT_CHAT

    try:
        from agent.pipeline import ChatPipeline
        reply = ChatPipeline().run(text)
        print(f"\n{_BOLD}Assistant>{_RESET} {reply}")
        return 0
    except Exception as e:
        print(f"{_RED}Error:{_RESET} {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
