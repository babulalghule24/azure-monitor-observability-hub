"""VMCP inventory helper (extracted from vm_sku_alternative_with_Cost.py).

Contains the Azure Resource Graph logic behind the get_vm_inventory tool:
inventory_vm_skus plus its small helpers, kept faithful to the original file.
"""
from __future__ import annotations

import datetime as _dt
from collections import defaultdict
from typing import Any, Dict, Sequence

from azure.identity import DefaultAzureCredential

try:
    from azure.mgmt.resourcegraph import ResourceGraphClient
    from azure.mgmt.resourcegraph.models import QueryRequest
    _ARG_IMPORT_ERROR: Exception | None = None
except ImportError as exc:  # keep the real reason so the tool can report it
    ResourceGraphClient = None  # type: ignore
    QueryRequest = None  # type: ignore
    _ARG_IMPORT_ERROR = exc


def _now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def normalize_region(region: str) -> str:
    return (region or "").strip().lower().replace(" ", "")


def inventory_vm_skus(credential: DefaultAzureCredential, subscriptions: Sequence[str]) -> Dict[str, Any]:
    if _ARG_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Could not import azure-mgmt-resourcegraph. Install it in the SAME environment "
            "that runs the server ('pip install azure-mgmt-resourcegraph'), then RESTART the "
            f"server. Original import error: {_ARG_IMPORT_ERROR!r}"
        )

    rg_client = ResourceGraphClient(credential)

    query = """
resources
| where type =~ 'microsoft.compute/virtualmachines' or type =~ 'microsoft.compute/virtualmachinescalesets'
| extend vmSize = case(
    type =~ 'microsoft.compute/virtualmachines', tostring(properties.hardwareProfile.vmSize),
    type =~ 'microsoft.compute/virtualmachinescalesets', tostring(sku.name),
    ''
  )
| project subscriptionId, resourceGroup, name, type, location, zones, vmSize
"""

    req = QueryRequest(subscriptions=list(subscriptions), query=query, options={"resultFormat": "objectArray"})
    res = rg_client.resources(req)
    rows = res.data or []

    norm_rows = []
    for r in rows:
        loc = normalize_region(r.get("location"))
        zones = r.get("zones")
        if isinstance(zones, list):
            zlist = [str(z) for z in zones]
        elif zones is None:
            zlist = []
        else:
            zlist = [z.strip() for z in str(zones).strip("[]").replace("'", "").split(",") if z.strip()]
        norm_rows.append(
            {
                "subscriptionId": r.get("subscriptionId"),
                "resourceGroup": r.get("resourceGroup"),
                "name": r.get("name"),
                "type": r.get("type"),
                "location": loc,
                "zones": zlist,
                "vmSize": r.get("vmSize"),
            }
        )

    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for r in norm_rows:
        reg = r["location"] or "unknown"
        sku = r["vmSize"] or "unknown"
        if r["zones"]:
            for z in r["zones"]:
                agg[reg][str(z)][sku] += 1
        else:
            agg[reg]["regional"][sku] += 1

    return {
        "generatedAt": _now_iso(),
        "subscriptions": list(subscriptions),
        "items": norm_rows,
        "aggregates": {reg: {zone: dict(skus) for zone, skus in zones.items()} for reg, zones in agg.items()},
    }
