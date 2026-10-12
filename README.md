# truenas-ws-mcp

An MCP (Model Context Protocol) server for **TrueNAS Scale** that connects via the native WebSocket API. Gives AI assistants like Claude full visibility and control over your TrueNAS homelab — storage pools, datasets, apps, VMs, snapshots, SMART tests, and more.

## Features

- **61 tools** covering storage, apps, VMs, snapshots, sharing, networking, SMART, cloud sync, and system management
- Native **WebSocket DDP** protocol (same as the TrueNAS UI uses)
- Works with TrueNAS Scale 24.10+ (Electric Eel and newer); see [Compatibility](#compatibility)
- Runs as a standard MCP server via `stdio` transport

## Quick Start

### Install

```bash
# With uv (recommended)
uvx truenas-ws-mcp

# With pip
pip install truenas-ws-mcp
```

### Configure

Set these environment variables (or create a `.env` file):

| Variable | Required | Default | Description |
|---|---|---|---|
| `TRUENAS_API_KEY` | Yes | — | API key from TrueNAS (System > API Keys) |
| `TRUENAS_URL` | No | `wss://truenas.local/websocket` | WebSocket URL of your TrueNAS instance |
| `TRUENAS_VERIFY_SSL` | No | `false` | SSL certificate verification |
| `TRUENAS_TIMEOUT` | No | `30` | API call timeout in seconds |

The URL is flexible — you can pass `https://192.168.1.100`, `wss://truenas.local/websocket`, or just a hostname. It will be normalized automatically.

### Add to Claude Code

```json
{
  "mcpServers": {
    "truenas": {
      "command": "uvx",
      "args": ["truenas-ws-mcp"],
      "env": {
        "TRUENAS_API_KEY": "your-api-key-here",
        "TRUENAS_URL": "wss://your-truenas-ip/websocket"
      }
    }
  }
}
```

### Add to Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "truenas": {
      "command": "uvx",
      "args": ["truenas-ws-mcp"],
      "env": {
        "TRUENAS_API_KEY": "your-api-key-here",
        "TRUENAS_URL": "wss://your-truenas-ip/websocket"
      }
    }
  }
}
```

## Compatibility

| TrueNAS Scale | Status |
|---|---|
| 25.10 (Goldeye) | Tested on 25.10.7 |
| 25.04 (Fangtooth) | Expected to work, not tested |
| 24.10 (Electric Eel) | Expected to work, not tested |

The TrueNAS API renames methods between releases. Where a tool depends on a renamed
method, it tries the newest name first and falls back to the older one only when the
server reports the method as missing (`[ENOMETHOD]`), so one install works across
versions. Tools that only work on some versions are marked in the list below.

## Available Tools

Markers: ¹ uses a newer API name with automatic fallback for older releases;
² not available on 25.10+ (the SMART test API was removed).

### Storage (8 tools)
`list_pools`, `get_pool_status`, `list_datasets`, `get_dataset`, `create_dataset`, `update_dataset`, `delete_dataset`

### Snapshots (6 tools)
`list_snapshots`¹, `create_snapshot`, `delete_snapshot`, `rollback_snapshot`, `clone_snapshot`, `list_snapshot_tasks`

### Apps (10 tools)
`list_apps`, `get_app_config`, `update_app_config`, `install_app`, `delete_app`, `start_app`, `stop_app`, `upgrade_app`, `redeploy_app`, `list_available_apps`

### VMs (4 tools)
`list_vms`, `start_vm`, `stop_vm`, `update_vm`

### Sharing (6 tools)
`list_smb_shares`, `create_smb_share`, `delete_smb_share`, `list_nfs_exports`, `create_nfs_export`, `delete_nfs_export`

### System (7 tools)
`system_info`, `list_alerts`, `list_services`, `list_jobs`, `get_audit_log`, `list_cron_jobs`, `get_boot_pool`

### Disks & SMART (4 tools)
`list_disks`, `get_disk_temps`, `list_smart_results`², `run_smart_test`²

### Network (2 tools)
`list_interfaces`, `get_network_config`

### Cloud & Replication (4 tools)
`list_cloud_syncs`, `run_cloud_sync`, `list_replications`, `run_replication`

### Reporting (2 tools)
`list_graphs`, `get_reporting_data`

### Users (5 tools)
`list_users`, `get_user`, `create_user`, `update_user`, `delete_user`

### Updates & Certs (2 tools)
`check_updates`¹, `list_certificates`

## Important Notes

- **App config updates are REPLACE, not MERGE.** When using `update_app_config`, send ALL storage/config keys — omitted keys revert to defaults.
- **VM RAM/CPU changes require a full stop+start** from TrueNAS. Rebooting from inside the VM does NOT re-allocate resources.
- **Destructive operations** (delete dataset, snapshot, share, user, app) require `confirm=True` as a safety guard.
- **Self-signed certs** are common in homelabs. SSL verification is off by default.
- **List tools are bounded.** `list_jobs`, `list_datasets`, and `list_snapshots` return compact,
  newest-first summaries capped by a `limit` argument, so large systems don't time out or flood
  the model's context. Use `get_dataset` for every property of a single dataset.

## Development

```bash
git clone https://github.com/thoriphes/truenas-ws-mcp.git
cd truenas-ws-mcp
uv sync
cp env.example .env
# Edit .env with your TrueNAS credentials
uv run pytest
```

## License

MIT
