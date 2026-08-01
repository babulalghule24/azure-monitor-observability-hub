#!/usr/bin/env python3
"""
generate-azuredeploy.py

Rebuilds azuredeploy.json from workbook.json so the ARM template's embedded
workbook (serializedData) never drifts out of sync with the real workbook
definition.

Why this exists:
    An Azure Monitor workbook ARM template carries the workbook content inside
    the resource property "serializedData" as an ESCAPED JSON STRING. If that
    string is empty ("{}") or stale, "Deploy to Azure" produces a blank or
    outdated workbook. This script reads the source workbook.json and writes a
    fresh azuredeploy.json with the content correctly embedded.

Usage:
    # Run from the workbook folder (defaults shown):
    python generate-azuredeploy.py

    # Or specify paths explicitly:
    python generate-azuredeploy.py \
        --workbook workbook.json \
        --output azuredeploy.json \
        --display-name "Azure VM Capacity Restrictions (v1-v4)"

After running, commit the updated azuredeploy.json to your repo.
"""

import argparse
import json
import sys
from pathlib import Path


def normalize_groups(workbook: dict) -> int:
    """Normalize workbook group items to the canonical Azure Workbooks form.

    Azure Workbooks only recognizes group content with
    "version": "NotebookGroup/1.0". A non-canonical version string such as
    "GroupItem/1.0" causes Azure to silently DROP the group's inline items on
    load, producing empty tabs. This walks every group item (type 12) at any
    nesting depth and rewrites the wrapper to the canonical form while keeping
    all nested items intact. Returns the number of groups changed.
    """
    changed = 0

    def walk(items):
        nonlocal changed
        for it in items:
            content = it.get("content", {})
            if it.get("type") == 12:
                if content.get("version") != "NotebookGroup/1.0" or "groupType" not in content:
                    content["version"] = "NotebookGroup/1.0"
                    content.setdefault("groupType", "editable")
                    content.pop("style", None)
                    changed += 1
            nested = content.get("items")
            if isinstance(nested, list):
                walk(nested)

    walk(workbook.get("items", []))
    return changed


def build_template(workbook: dict, display_name: str) -> dict:
    """Return an ARM template dict with the workbook embedded in serializedData."""
    normalize_groups(workbook)
    serialized = json.dumps(workbook, separators=(",", ":"))
    return {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "workbookDisplayName": {
                "type": "string",
                "defaultValue": display_name,
                "metadata": {
                    "description": "The friendly name for the workbook shown in the Gallery or Saved List. Must be unique in the resource group."
                },
            },
            "workbookType": {
                "type": "string",
                "defaultValue": "workbook",
                "metadata": {
                    "description": "The gallery the workbook is shown under (e.g. workbook, tsg, Azure Monitor)."
                },
            },
            "workbookSourceId": {
                "type": "string",
                "defaultValue": "Azure Monitor",
                "metadata": {
                    "description": "Resource id the workbook is associated with. 'Azure Monitor' is used for a resource-independent workbook."
                },
            },
            "workbookId": {
                "type": "string",
                "defaultValue": "[newGuid()]",
                "metadata": {
                    "description": "Unique guid for this workbook instance."
                },
            },
        },
        "resources": [
            {
                "type": "Microsoft.Insights/workbooks",
                "apiVersion": "2022-04-01",
                "name": "[parameters('workbookId')]",
                "location": "[resourceGroup().location]",
                "kind": "shared",
                "properties": {
                    "displayName": "[parameters('workbookDisplayName')]",
                    "serializedData": serialized,
                    "version": "1.0",
                    "sourceId": "[parameters('workbookSourceId')]",
                    "category": "[parameters('workbookType')]",
                },
            }
        ],
        "outputs": {
            "workbookId": {
                "type": "string",
                "value": "[resourceId('Microsoft.Insights/workbooks', parameters('workbookId'))]",
            }
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild azuredeploy.json from workbook.json."
    )
    parser.add_argument(
        "--workbook", default="workbook.json", help="Path to the source workbook JSON."
    )
    parser.add_argument(
        "--output", default="azuredeploy.json", help="Path to write the ARM template."
    )
    parser.add_argument(
        "--display-name",
        default="Azure VM Capacity Restrictions (v1-v4)",
        help="Default workbook display name baked into the template.",
    )
    args = parser.parse_args()

    workbook_path = Path(args.workbook)
    if not workbook_path.is_file():
        print(f"ERROR: workbook file not found: {workbook_path}", file=sys.stderr)
        return 1

    try:
        workbook = json.loads(workbook_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: {workbook_path} is not valid JSON: {e}", file=sys.stderr)
        return 1

    items = workbook.get("items")
    if not isinstance(items, list) or len(items) == 0:
        print(
            f"WARNING: {workbook_path} has no 'items' — the workbook may be empty.",
            file=sys.stderr,
        )

    normalized = normalize_groups(workbook)
    if normalized:
        print(f"Normalized {normalized} group item(s) to 'NotebookGroup/1.0'.")

    template = build_template(workbook, args.display_name)

    # Validate the embedded string round-trips before writing.
    embedded = json.loads(template["resources"][0]["properties"]["serializedData"])
    assert embedded == workbook, "Round-trip mismatch — embedding failed."

    output_path = Path(args.output)
    output_path.write_text(json.dumps(template, indent=2), encoding="utf-8")

    print(f"OK  Wrote {output_path}")
    print(f"    Embedded items: {len(items) if isinstance(items, list) else 0}")
    print(f"    serializedData length: {len(template['resources'][0]['properties']['serializedData'])} chars")
    print("    Next step: commit the updated azuredeploy.json to your repo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
