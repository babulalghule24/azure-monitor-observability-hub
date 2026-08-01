# Azure VM Capacity Restrictions (v1-v4)

## Overview

Azure Monitor Workbook to identify Azure VM series impacted by Microsoft's v1-v4 VM capacity restrictions and retirement announcements.

## Features

- Subscription-level analysis
- Region-level analysis
- Impacted VM inventory
- Migration recommendations
- Capacity risk assessment
- Export to Excel support
- Azure Resource Graph powered

---

## Deployment Options

### Option 1: Import Workbook JSON

1. Open Azure Portal
2. Navigate to **Azure Monitor**
3. Select **Workbooks**
4. Click **New**
5. Click **Advanced Editor (</>)**
6. Remove the default content
7. Open `workbook.json`
8. Copy the entire file contents
9. Paste into Advanced Editor
10. Click **Apply**
11. Click **Done Editing**
12. Save the workbook

---

### Option 2: Deploy to Azure

🚧 Coming soon

This repository will include:

- Deploy to Azure button
- ARM template
- Parameter file
- Automated deployment

---

## Files

| File | Description |
|------|-------------|
| workbook.json | Workbook source |
| azuredeploy.json | ARM deployment template |
| azuredeploy.parameters.json | Deployment parameters |
| README.md | Documentation |

---

## Author

**Babulal Ghule**  
Cloud Solution Architect  
Microsoft SfMC