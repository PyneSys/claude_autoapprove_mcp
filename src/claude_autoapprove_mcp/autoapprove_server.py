#! /usr/bin/env python3
import asyncio
import sys
import psutil
import time
import subprocess
import argparse
import multiprocessing

from claude_autoapprove.claude_autoapprove import inject_script, DEFAULT_PORT, get_claude_config, \
    get_trusted_tools, is_port_open, start_claude

from fastmcp import FastMCP

mcp = FastMCP(
    name="Claude Auto-Approve MCP",
    instructions="This MCP is for automatically injecting the claude-autoapprove script into the Claude Desktop app."
)

claude_config = get_claude_config()


def eprint(*args, **kwargs):
    """
    Print to stderr for diagnostic messages.

    :param args: Arguments to print.
    :param kwargs: Keyword arguments to print.
    """
    print(*args, file=sys.stderr, **kwargs)


def get_main_claude_pid():
    """
    Find the main Claude process and return its PID.

    For Electron apps, find the oldest process that isn't a renderer.

    :return: PID of the main Claude process, or None if not found.
    :rtype: int or None
    """
    claude_processes = []

    # First collect all processes that look like Claude
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if sys.platform == "darwin":  # macOS
                if proc.name() == "Claude" and "Claude.app" in str(proc.cmdline()):
                    claude_processes.append(proc)
            elif sys.platform == "win32":  # Windows
                if "Claude.exe" in str(proc.name()) or "Claude.exe" in str(proc.cmdline()):
                    claude_processes.append(proc)
            else:
                eprint(f"Unsupported platform: {sys.platform}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if not claude_processes:
        return None

    # For Electron apps, identify main process vs renderers
    main_candidates = []

    for proc in claude_processes:
        try:
            # The main Electron process typically doesn't have "--type=renderer" in command line
            # and is the oldest process in the group
            cmdline = " ".join(proc.cmdline()).lower()
            if "--type=renderer" not in cmdline:
                main_candidates.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # If we found main candidates, return the oldest one
    if main_candidates:
        oldest = sorted(main_candidates, key=lambda p: p.create_time())[0]
        return oldest.pid

    # Fallback: return the oldest Claude process
    oldest = sorted(claude_processes, key=lambda p: p.create_time())[0]
    return oldest.pid


def terminate_claude_process(pid):
    """
    Terminate a Claude process given its PID.

    :param pid: PID of the Claude process to terminate.
    :type pid: int

    :return: True if successfully terminated, False otherwise.
    :rtype: bool
    """
    if pid is None:
        return False

    # Try platform-specific graceful quit first
    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "Claude" to quit'],
                check=False
            )
            time.sleep(1)

            # Check if process still exists
            try:
                proc = psutil.Process(pid)
                if not proc.is_running():
                    return True
            except psutil.NoSuchProcess:
                return True

        except Exception as e:
            eprint(f"AppleScript quit failed: {e}")

    elif sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/IM", "Claude.exe"],
                check=False
            )
            time.sleep(1)

            # Check if process still exists
            try:
                proc = psutil.Process(pid)
                if not proc.is_running():
                    return True
            except psutil.NoSuchProcess:
                return True

        except Exception as e:
            eprint(f"taskkill failed: {e}")

    # Fall back to direct process termination
    try:
        proc = psutil.Process(pid)
        eprint(f"Terminating Claude process {pid}...")
        proc.terminate()

        # Wait for process to terminate
        try:
            proc.wait(timeout=5)
            return True
        except psutil.TimeoutExpired:
            # Force kill if still alive
            eprint(f"Force killing Claude process {pid}...")
            proc.kill()

            try:
                proc.wait(timeout=2)
                return True
            except psutil.TimeoutExpired:
                return False

    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        eprint(f"Error accessing Claude process {pid}: {e}")
        return False
    except Exception as e:
        eprint(f"Error killing Claude process: {e}")
        return False


def claude_restart_worker(port):
    """
    Worker function that runs in a separate process.

    This function handles the entire restart process:
        1. Identifies the main Claude process
        2. Terminates it
        3. Waits for termination
        4. Starts a new instance with the debugging port

    :param port: Port to use for the new Claude instance.
    :type port: int
    """

    # Log worker startup
    eprint(f"Restart worker started - will restart Claude with port: {port}")

    try:
        # 1. Identify the main Claude process
        eprint("Identifying main Claude process...")
        claude_pid = get_main_claude_pid()

        if claude_pid:
            eprint(f"Found main Claude process: PID {claude_pid}")

            # 2. Terminate the process
            eprint(f"Terminating Claude process {claude_pid}...")

            if terminate_claude_process(claude_pid):
                eprint(f"Claude process {claude_pid} terminated successfully")
            else:
                eprint(f"Failed to terminate Claude process {claude_pid}")

            # 3. Wait to make sure the process is completely terminated
            max_wait = 10  # seconds
            terminated = False

            for _ in range(max_wait):
                try:
                    proc = psutil.Process(claude_pid)
                    if not proc.is_running():
                        terminated = True
                        eprint(f"Confirmed Claude process {claude_pid} is terminated")
                        break
                except psutil.NoSuchProcess:
                    terminated = True
                    eprint(f"Confirmed Claude process {claude_pid} no longer exists")
                    break

                time.sleep(1)

            if not terminated:
                eprint(f"Warning: Claude process {claude_pid} may still be running")
        else:
            eprint("No Claude process found to terminate")

        # 5. Start Claude with the debugging port
        eprint(f"Starting Claude with debugging port {port}...")

        try:
            start_claude(port)
        except Exception as e:
            eprint(f"Error starting Claude: {e}")
            return 1

        eprint("Restart worker completed its task successfully")

    except Exception as e:
        eprint(f"Unexpected error in restart worker: {e}")


def main(args=None):
    """
    Main entry point for the Claude Auto-Approve MCP server.

    :param args: Optional argparse.Namespace object with parsed arguments.
    :type args: argparse.Namespace or None
    :return: 1 if error occurred, otherwise None.
    :rtype: int or None
    """
    if args is None:
        parser = argparse.ArgumentParser(description="Claude Auto-Approve MCP server")
        parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Debugger port for Claude Desktop")
        args = parser.parse_args()

    port = args.port

    # Check if Claude Desktop is running with the debugger port
    if not is_port_open(port):
        eprint(f"Claude Desktop is not listening on port {port}")

        # Start a worker process to handle the entire restart process
        eprint("Starting worker process to handle Claude restart...")
        worker = multiprocessing.Process(
            target=claude_restart_worker,
            args=(port,),
            daemon=False  # Important: daemon=False ensures worker survives if parent exits
        )
        worker.start()
        eprint(f"Worker process started with PID: {worker.pid}")

        # Exit this process, letting the worker handle everything
        eprint("Exiting main process. Worker will handle Claude restart.")
        sys.exit(0)

    # If we get here, Claude is already running with the debugger port
    # Inject script and start MCP server
    try:
        eprint(f"Claude is in debug mode, injecting script into it...")
        asyncio.run(inject_script(claude_config, port))
        eprint("Script injected successfully, starting MCP server...")
        mcp.run()
    except Exception as e:
        eprint(f"Error injecting script or starting MCP: {e}")
        return 1


if __name__ == "__main__":
    main()


#
# Tools
#

@mcp.tool()
def autoapproved_tools() -> list[str]:
    """
    List all the tools that have been auto-approved in the configuration.

    :return: List of auto-approved tool names.
    :rtype: list[str]
    """
    return get_trusted_tools(claude_config)
