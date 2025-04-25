# Claude Auto-Approve MCP

An MCP to restart Claude Desktop App with enabled debugger port and inject a JavaScript into it, which extends Claude with MCP auto-approve functionality.
It uses the [claude-autoapprove](https://github.com/PyneSys/claude_autoapprove) library under the hood.

## How it works

The MCP server will restart the Claude Desktop App with enabled debugger port and inject a JavaScript into it, which extends Claude with MCP auto-approve functionality.

Dont't be afraid when after 1st start of the app it will be closed immediately. This is expected behavior.

## Installation

### Imstalling `uv` (if you don't have it yet)

After installing `uv`, make sure it's available in your **PATH**.

#### MacOS

##### Brew
```bash
brew install uv
```

##### MacPorts
```bash
sudo port install uv
```

#### Windows

```bash
winget install --id=astral-sh.uv  -e
```

#### Other installation options

You can find other installation options in the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

### Add it to your `claude_desktop_config.json`

```json
{
    "mcpServers": {
        "claude-autoapprove-mcp": {
            "command": "uvx",
            "args": [
                "claude-autoapprove-mcp"
            ],
            "autoapprove": [
                "autoapproved_tools",
                "autoblocked_tools"
            ]
        }
    }
}
```

Restart Claude Desktop if it is already running.

#### Arguments

| Parameter    | Description |
|--------------|-------------|
| `port` | Optional. The port number to listen on, default is 19222 |
| `persist` | Optional. Works only on macOS (atm). If specified, it installs a little wathcer script, which will restart Claude Desktop with enabled debugger port, if it is not running with debugger port. This allows early detection and automatic restart, so you don't need to wait for one restart (only the first time). It also installs a LaunchAgent, so it will be started at login. If you remove the `--persist` argument, the watcher script will be removed and the LaunchAgent will be uninstalled. |

```json
{
    "mcpServers": {
        "claude-autoapprove-mcp": {
            "command": "uvx",
            "args": [
                "claude-autoapprove-mcp",
                "--port", "19222",
                "--persist"
            ]
        }
    }
}
```

## Configuration

You can add `autoapprove` and `autoblock` parameters to each MCP server, the `claude-autoapprove-mcp` will read that configuration and apply it to the running instance.

| Parameter    | Description |
|--------------|-------------|
| `autoapprove` | List of tool names that should be automatically approved |
| `autoblock`   | List of tool names that should be automatically blocked |


```json
{
    "mcpServers": {
        "claude-autoapprove-mcp": {
        "command": "uvx",
            "args": [
                "claude-autoapprove-mcp"
            ],
        "autoapprove": [
            "autoapproved_tools"
        ],
        "autoblock": [
        ]
    },
    "project-mem-mcp": {
        "command": "uvx",
        "args": [
            "project-mem-mcp",
            "--allowed-dir", "/Users/wallner/Developer/MCP",
            "--allowed-dir", "/Users/wallner/Developer/Projects/ByCompany/BacktestGuy"
        ],
        "autoapprove": [
            "get_project_memory",
            "set_project_memory",
            "update_project_memory"
        ],
        "autoblock": [
        ]
    },
    "browsermcp": {
      "command": "npx",
      "args": [
        "@browsermcp/mcp@latest"
      ],
      "autoapprove": [
        "browser_get_console_logs",
        "browser_snapshot"
      ],
      "autoblock": [
        "browser_screenshot"
      ]
    }
}
```


## Usage

Just run Claude Desktop. It is not invasive, it doesn't change anything in the app (only if you use the `--persist` argument), just injects a JavaScript into the running instance. So you can install updates as usual (even when using the `--persist` argument).
It uses a feature of most Electron based apps: [remote debugging port](https://www.electronjs.org/docs/latest/api/command-line-switches#--remote-debugging-portport).

If you want to list all tools that are auto-approved, you can use the following prompt in Claude Desktop:
```
list all tools that are auto-approved
```

If you want to list all tools that are auto-blocked, you can use the following prompt in Claude Desktop:
```
list all tools that are auto-blocked
```

## Security

The remote debugging port allows any application on your localhost (your machine) to connect to the running Claude Desktop App. This may be a security risk, because any app or script can connect to it and execute arbitrary code inside Claude Desktop App context. This may be used for malicious purposes. It is a low risk, if you know what is running on your computer.

So be careful when using this feature and use it at your own risk.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

If you want to contribute to this project, please fork the repository and create a pull request.
