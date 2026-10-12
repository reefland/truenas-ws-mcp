from truenas_ws_mcp.server import mcp, get_client


@mcp.tool
async def check_updates() -> dict:
    """Check for available TrueNAS system updates (current train/version and any new version)."""
    client = await get_client()
    # update.status replaced update.check_available in TrueNAS 25.10.
    return await client.call_first([("update.status", []), ("update.check_available", [])])


@mcp.tool
async def list_certificates() -> list:
    """List all SSL/TLS certificates."""
    client = await get_client()
    return await client.call("certificate.query", [])
