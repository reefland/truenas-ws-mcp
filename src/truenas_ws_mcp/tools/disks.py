"""Disk information tools for TrueNAS."""

from truenas_ws_mcp.server import mcp, get_client


@mcp.tool()
async def list_disks() -> list:
    """List all disks with model, serial number, size, and pool membership."""
    client = await get_client()
    disks = await client.call("disk.query", [])
    return [
        {
            "name": d.get("name"),
            "model": d.get("model"),
            "serial": d.get("serial"),
            "size": d.get("size"),
            "pool": d.get("pool"),
        }
        for d in disks
    ]


@mcp.tool()
async def get_disk_temps() -> list:
    """Get current temperatures for all disks."""
    client = await get_client()
    disks = await client.call("disk.query", [[], {"select": ["name"]}])
    # One call for every disk. The old per-disk reporting.netdata_graph
    # ("disktemp", {"identifier": ...}) query fails on TrueNAS 25.10 with
    # "query.identifier: Extra inputs are not permitted".
    temps = await client.call("disk.temperatures", [])

    results = []
    for d in disks:
        disk_name = d.get("name")
        if not disk_name:
            continue
        temp = temps.get(disk_name)
        if temp is None:
            results.append({"disk": disk_name, "temperature": None, "error": "unable to retrieve temperature"})
        else:
            results.append({"disk": disk_name, "temperature": temp})

    return results
