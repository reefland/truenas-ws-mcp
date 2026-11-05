from truenas_ws_mcp.server import mcp, get_client


@mcp.tool()
async def list_graphs() -> list:
    """List available reporting graphs and their identifiers.

    Available graphs include: cpu, cputemp, memory, disk, interface, load,
    uptime, arcsize, disktemp, and more. Some graphs require an identifier
    (disk name for 'disk'/'disktemp', interface name for 'interface').
    """
    client = await get_client()
    return await client.call("reporting.graphs", [])


@mcp.tool()
async def get_reporting_data(
    graph: str,
    unit: str = "HOUR",
    identifier: str | None = None,
) -> list:
    """Get historical reporting data for a graph.

    Units: HOUR (1h), DAY (24h), WEEK, MONTH, YEAR. Some graphs need an
    identifier (e.g., disk name 'sda' for disk graphs, interface name
    'enp5s0' for network graphs). Response format:
    [{name, identifier, data: [[unix_timestamp, value], ...]}].
    Memory/ARC values in bytes, CPU in percentage.
    """
    query = {"unit": unit, "page": 1}
    client = await get_client()
    if identifier is None:
        return await client.call("reporting.netdata_graph", [graph, query])

    # TrueNAS 25.10 rejects "identifier" inside the netdata_graph query
    # ("Extra inputs are not permitted"); it has to go through
    # reporting.get_data instead. Disk graphs there are keyed by a full label
    # such as "sda | Type: HDD | Model: ... | Serial: ...", and a bare "sda"
    # silently matches nothing, so resolve the short name to the full label.
    graphs = await client.call("reporting.graphs", [[["name", "=", graph]]])
    known = (graphs[0].get("identifiers") or []) if graphs else []
    if identifier not in known:
        matches = [i for i in known if i.split(" | ", 1)[0] == identifier]
        if len(matches) != 1:
            raise ValueError(
                f"Unknown identifier {identifier!r} for graph {graph!r}. "
                f"Available: {known}"
            )
        identifier = matches[0]
    return await client.call(
        "reporting.get_data", [[{"name": graph, "identifier": identifier}], query]
    )
