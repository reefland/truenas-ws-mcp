"""Storage pool and dataset management tools."""
from __future__ import annotations

from truenas_ws_mcp.server import get_client, mcp


# Compact dataset summary: the default query returns every ZFS property (with
# parsed/raw/source variants) plus nested child trees, which takes minutes and
# hundreds of KB on real pools.
_DATASET_PROPERTIES = ["used", "available", "quota", "refquota", "compression", "compressratio", "mountpoint"]
_DATASET_OPTIONS = {
    "select": ["id", "type", *_DATASET_PROPERTIES],
    "extra": {"flat": True, "retrieve_children": False, "properties": _DATASET_PROPERTIES},
}


def _summarize_dataset(ds: dict) -> dict:
    summary = {"name": ds.get("id"), "type": ds.get("type")}
    for prop in _DATASET_PROPERTIES:
        value = ds.get(prop)
        summary[prop] = value.get("value") if isinstance(value, dict) else value
    return summary


@mcp.tool()
async def list_pools() -> list:
    """List all storage pools with health, capacity, and fragmentation."""
    client = await get_client()
    return await client.call("pool.query", [])


@mcp.tool()
async def get_pool_status(pool_name: str) -> dict:
    """Get detailed pool status with VDEV topology and error counts."""
    client = await get_client()
    results = await client.call("pool.query", [[["name", "=", pool_name]]])
    if not results:
        raise ValueError(f"Pool '{pool_name}' not found")
    return results[0]


@mcp.tool()
async def list_datasets(pool: str | None = None, limit: int = 200) -> list:
    """List datasets (flat) with used/available space, quota, compression, and mountpoint."""
    client = await get_client()
    # An empty filter only returns pool roots in flat mode, so always filter on pool.
    filters = [["pool", "=", pool]] if pool else [["pool", "!=", ""]]
    datasets = await client.call("pool.dataset.query", [filters, {**_DATASET_OPTIONS, "limit": limit}])
    return [_summarize_dataset(ds) for ds in datasets]


@mcp.tool()
async def get_dataset(name: str) -> dict:
    """Get detailed info for a specific dataset."""
    client = await get_client()
    # Without retrieve_children=False a pool-root dataset returns its whole tree.
    results = await client.call(
        "pool.dataset.query", [[["id", "=", name]], {"extra": {"retrieve_children": False}}]
    )
    if not results:
        raise ValueError(f"Dataset '{name}' not found")
    return results[0]


@mcp.tool()
async def create_dataset(
    name: str,
    type: str = "FILESYSTEM",
    compression: str | None = None,
    quota: int | None = None,
    recordsize: str | None = None,
    comments: str | None = None,
) -> dict:
    """Create a new ZFS dataset."""
    client = await get_client()
    payload: dict = {"name": name, "type": type}
    if compression is not None:
        payload["compression"] = compression
    if quota is not None:
        payload["quota"] = quota
    if recordsize is not None:
        payload["recordsize"] = recordsize
    if comments is not None:
        payload["comments"] = comments
    return await client.call("pool.dataset.create", [payload])


@mcp.tool()
async def update_dataset(name: str, properties: dict) -> dict:
    """Update dataset properties (compression, quota, comments, etc.)."""
    client = await get_client()
    return await client.call("pool.dataset.update", [name, properties])


@mcp.tool()
async def delete_dataset(name: str, confirm: bool = False) -> str:
    """Delete a dataset. Requires confirm=True."""
    if not confirm:
        return "Error: You must pass confirm=True to delete a dataset. This action is irreversible."
    client = await get_client()
    await client.call("pool.dataset.delete", [name])
    return f"Dataset '{name}' deleted successfully."
