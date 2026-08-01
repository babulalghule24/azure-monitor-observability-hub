# Azure VM Capacity Restrictions (v1-v4)

https://img.shields.io/badge/Azure-Monitor-blue
https://img.shields.io/badge/Azure-Workbook-green
![Azure Resource Graph](https://img.shields.io/badgeorange

## Overview

Azure Monitor Workbook to identify Azure VM series impacted by Microsoft's v1-v4 VM capacity restrictions and retirement announcements.

This workbook provides visibility into:

- Capacity growth restrictions effective July 31, 2026
- VM retirement timelines
- Subscription-level capacity risks
- Migration planning requirements
- Scale-out limitations
- Quota increase restrictions

---

## Features

- Subscription-level analysis
- Region-level analysis
- Impacted VM inventory
- Migration recommendations
- Capacity risk assessment
- Export to Excel support
- Azure Resource Graph powered
- Interactive filtering
- Executive summary dashboard

---

# Deployment Options

## Option 1 - Manual Import

### Download Workbook

Download:

- `workbook.json`

### Import into Azure Monitor

1. Open Azure Portal
2. Navigate to:

```text
Azure Monitor
   → Workbooks
   → New
```

3. Select **Advanced Editor (</>)**
4. Delete existing content
5. Open `workbook.json`
6. Copy the entire file contents
7. Paste into Advanced Editor
8. Click **Apply**
9. Click **Done Editing**
10. Save the workbook

---

## Option 2 - Deploy to Azure (Coming Soon)

A one-click deployment experience will be added soon.

Files to be added:

- azuredeploy.json
- azuredeploy.parameters.json
- Deploy to Azure button

Example:

```markdown
https://aka.ms/deploytoazurebutton](<DEPLOY_URL>)
```

---

# Repository Contents

| File | Description |
|--------|-------------|
| workbook.json | Workbook definition |
| README.md | Documentation |
| azuredeploy.json | ARM deployment template (coming soon) |
| azuredeploy.parameters.json | ARM deployment parameters (coming soon) |

---

# Data Sources

This workbook uses:

- Azure Resource Graph
- Azure Resource Manager metadata
- Azure Subscription inventory
- Azure VM SKU information

No Log Analytics workspace is required.

---

# Workbook Tabs

## Overview

Provides:

- Total impacted VMs
- Impact categories
- Version distribution
- Subscription overview
- Regional overview

## Affected VMs

Detailed inventory of:

- VM Name
- VM Size
- Region
- Subscription
- Impact Level
- Retirement Date
- Recommended Replacement SKU

## Migration Plan

Provides:

- Recommended migration targets
- SKU modernization guidance
- Retirement priorities
- Migration workload sizing

## Capacity Risk

Highlights:

- Growth-blocked subscriptions
- Regions at risk
- Capacity expansion concerns
- Quota limitations

## Guidance & Resources

Includes:

- Microsoft migration guidance
- Retirement information
- VM resize documentation
- New generation VM recommendations

---

# Prerequisites

Minimum permissions:

```text
Reader
```

Recommended permissions:

```text
Reader
Monitoring Reader
Resource Graph Reader
```

---

# Supported VM Families

## Retiring and Capacity Restricted

- D
- Ds
- Dv2
- Dsv2
- Av2
- Amv2
- B
- Bs
- F
- Fs
- Fsv2
- G
- Gs
- Ls
- Lsv2

## Growth Controlled

- Dv3
- Dsv3
- Dv4
- Dsv4
- Ddv4
- Ddsv4
- Dav4
- Dasv4
- Ev3
- Esv3
- Ev4
- Esv4
- Edv4
- Edsv4
- Eav4
- Easv4

---

# Author

**Babulal Ghule**  
Cloud Solution Architect  
Microsoft SfMC

---

# License

MIT License