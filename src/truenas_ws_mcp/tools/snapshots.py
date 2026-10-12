from truenas_ws_mcp.server import mcp, get_client


@mcp.tool
async def list_snapshots(dataset: str | None = None, limit: int = 100) -> list:
    """List ZFS snapshots (newest first) with creation time, used, and referenced size."""
    client = await get_client()
    filters = [["dataset", "=", dataset]] if dataset else []
    # Fetching every snapshot property costs ~0.6s and ~5KB per snapshot; ask for three.
    options = {
        "order_by": ["-createtxg"],
        "limit": limit,
        "extra": {"properties": ["creation", "used", "referenced"]},
    }
    # pool.snapshot.query is the 25.04+ name; zfs.snapshot.query is the older alias.
    snapshots = await client.call_first([
        ("pool.snapshot.query", [filters, options]),
        ("zfs.snapshot.query", [filters, options]),
    ])
    result = []
    for snap in snapshots:
        props = snap.get("properties") or {}
        result.append({
            "name": snap.get("name"),
            "dataset": snap.get("dataset"),
            **{key: (props.get(key) or {}).get("value") for key in ("creation", "used", "referenced")},
        })
    return result


@mcp.tool
async def create_snapshot(dataset: str, name: str, recursive: bool = False) -> dict:
    """Create a manual ZFS snapshot."""
    client = await get_client()
    return await client.call(
        "zfs.snapshot.create",
        [{"dataset": dataset, "name": name, "recursive": recursive}],
    )


@mcp.tool
async def delete_snapshot(snapshot_name: str, confirm: bool = False) -> str:
    """Delete a snapshot. Requires confirm=True. Snapshot format: dataset@name."""
    if not confirm:
        return "Error: confirm must be True to delete a snapshot."
    client = await get_client()
    await client.call("zfs.snapshot.delete", [snapshot_name])
    return f"Snapshot '{snapshot_name}' deleted."


@mcp.tool
async def rollback_snapshot(snapshot_name: str, confirm: bool = False) -> str:
    """Rollback dataset to snapshot. Requires confirm=True. WARNING: destroys newer data."""
    if not confirm:
        return "Error: confirm must be True to rollback a snapshot."
    client = await get_client()
    await client.call("zfs.snapshot.rollback", [snapshot_name])
    return f"Rolled back to snapshot '{snapshot_name}'."


@mcp.tool
async def clone_snapshot(snapshot_name: str, target_dataset: str) -> dict:
    """Clone a snapshot to a new dataset."""
    client = await get_client()
    return await client.call(
        "zfs.snapshot.clone",
        [{"snapshot": snapshot_name, "dataset_dst": target_dataset}],
    )


@mcp.tool
async def list_snapshot_tasks() -> list:
    """List automated snapshot task schedules."""
    client = await get_client()
    return await client.call("pool.snapshottask.query", [])
