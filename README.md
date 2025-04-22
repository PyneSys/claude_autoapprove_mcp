# claude-autoapprove-mcp

An MCP to restart Claude Desktop App with enabled debugger port and inject a JavaScript into it, which extends Claude with MCP auto-approve functionality.
It uses the [claude-autoapprove](https://github.com/PyneSys/claude_autoapprove) library under the hood.

> **Note:** Windows support is untested. If you try it on Windows, please share your experience! If it doesn't work, please help me to fix it!

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
                "autoapproved_tools"
            ]
        }
    }
}
```

Close the app and reopen it!

## Usage

There is no special usage. Just run Claude Desktop. It is not invasive, it doesn't change anything in the app, just injects a JavaScript into the running instance. So you can install updates as usual.
It uses a feature of all Electron based apps.

If you want to list all tools that are auto-approved, you can use the following prompt in Claude Desktop:
```
list all tools that are auto-approved
```
