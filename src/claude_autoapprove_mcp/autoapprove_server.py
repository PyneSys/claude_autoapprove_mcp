#! /usr/bin/env python3
from typing import Optional
import asyncio
import os
import sys
import psutil
import subprocess
from fastmcp import FastMCP
import argparse

from claude_autoapprove.claude_autoapprove import inject_script, DEFAULT_PORT, get_claude_config, \
    get_trusted_tools, is_port_open, start_claude

mcp = FastMCP(
    name="Claude Auto-Approve MCP",
    instructions="This MCP is for automatically injecting the claude-autoapprove script into the Claude Desktop app."
)

claude_config = get_claude_config()


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def find_claude_process():
    """
    Find Claude Desktop process across platforms.

    Returns:
        psutil.Process or None: The Claude process if found, None otherwise
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Different process names based on platform
            if sys.platform == "darwin":  # macOS
                if proc.name() == "Claude" or "Claude.app" in str(proc.cmdline()):
                    return proc
            elif sys.platform == "win32":  # Windows
                if "Claude.exe" in str(proc.name()) or "Claude.exe" in str(proc.cmdline()):
                    return proc
            elif sys.platform.startswith("linux"):  # Linux
                if "Claude" in str(proc.name()) or "Claude" in str(proc.cmdline()):
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None


def get_main_claude_process() -> Optional[psutil.Process]:
    """
    Walk up parent chain to find the main Claude application process.

    :returns: The main Claude process if found, otherwise None.
    :rtype: psutil.Process or None
    """
    # search up the parent-chain for the actual .app bundle binary on macOS
    current = psutil.Process(os.getpid())
    while current:
        try:
            exe_path = current.exe()
        except (psutil.AccessDenied, psutil.ZombieProcess, psutil.NoSuchProcess):
            exe_path = ""
        if 'Contents/MacOS/Claude' in exe_path:
            return current
        current = current.parent()
    # fallback: last ancestor named 'claude' or 'claude.exe'
    current = psutil.Process(os.getpid())
    candidate: Optional[psutil.Process] = None
    while current:
        name = current.name().lower()
        if name in ('claude', 'claude.exe'):
            candidate = current
        current = current.parent()
    return candidate


def kill_claude_process():
    """
    Terminate the main Claude Desktop process and its child processes if running.

    :returns: True if process was killed, False otherwise.
    :rtype: bool
    """
    # try OS-specific graceful quit before forceful termination
    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "Claude" to quit'],
                check=False
            )
            return True
        except Exception as e:
            eprint(f"AppleScript quit failed: {e}")
    elif sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/IM", "Claude.exe", "/T", "/F"],
                check=False
            )
            return True
        except Exception as e:
            eprint(f"taskkill failed: {e}")
    # detect main Claude process via parent-chain, fallback to simple finder
    proc = get_main_claude_process() or find_claude_process()
    if not proc:
        return False
    # terminate child processes first
    try:
        children = proc.children(recursive=True)
        for child in children:
            eprint(f"Terminating child process {child.pid}...")
            child.terminate()
        eprint(f"Terminating main Claude process {proc.pid}...")
        proc.terminate()
        # wait for processes to terminate
        wait_list = [proc] + children
        _, alive = psutil.wait_procs(wait_list, timeout=5)
        if alive:
            eprint(f"Force killing remaining processes: {[p.pid for p in alive]}...")
            for p in alive:
                p.kill()
        return True
    except Exception as e:
        eprint(f"Error killing Claude process: {e}")
    return False


def daemonize():
    """
    Daemonize the current process (Unix-like systems).
    """
    if sys.platform == "win32":
        # Windows doesn't support fork, use another approach
        return

    # First fork
    try:
        pid = os.fork()
        if pid > 0:
            # Exit first parent
            sys.exit(0)
    except OSError:
        sys.exit(1)

    # Decouple from parent environment
    os.chdir('/')
    os.setsid()
    os.umask(0)

    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            # Exit from second parent
            sys.exit(0)
    except OSError:
        sys.exit(1)

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    with open(os.devnull, 'r') as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open(os.devnull, 'a+') as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
    with open(os.devnull, 'a+') as f:
        os.dup2(f.fileno(), sys.stderr.fileno())


def start_in_background(args):
    """
    Start the script in background mode.
    """
    if sys.platform == "win32":
        # For Windows, use subprocess with creationflags
        subprocess.Popen(
            [sys.executable] + sys.argv,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            close_fds=True
        )
    else:
        # For Unix-like systems
        if os.fork() == 0:
            # Child process
            daemonize()
            main(args)
        else:
            # Parent process
            eprint("Started Claude Auto-Approve MCP in background.")
            sys.exit(0)


def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser(description="Claude Auto-Approve MCP server")
        parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Debugger port for Claude Desktop")
        parser.add_argument("--daemon", action="store_true", help=argparse.SUPPRESS)
        args = parser.parse_args()

    eprint(f"Starting Claude Auto-Approve MCP on port {args.port}...")

    if args.daemon:
        start_in_background(args)
        return

    # Check if Claude Desktop is running with the debugger port
    if not is_port_open(args.port):
        eprint(f"Claude Desktop is not listening on port {args.port}")

        # Kill existing Claude process if any
        eprint("Attempting to terminate existing Claude process...")
        if kill_claude_process():
            eprint("Existing Claude process terminated.")

        # Start Claude with debugger port
        eprint(f"Starting Claude with debugger port {args.port}...")

        try:
            start_claude(port=args.port)
        except TimeoutError as e:
            eprint(f"Failed to connect to port {args.port} after multiple attempts")
        except Exception as e:
            eprint(f"Error starting Claude: {e}")

        return

    # Inject script and start MCP server
    asyncio.run(inject_script(claude_config, args.port))
    mcp.run()


if __name__ == "__main__":
    main()


#
# Tools
#

@mcp.tool()
def autoapproved_tools() -> list[str]:
    """
    List all the tools that have been auto-approved in the configuration.
    """
    return get_trusted_tools(claude_config)
