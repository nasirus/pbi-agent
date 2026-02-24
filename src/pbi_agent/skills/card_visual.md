# Card Visual

Properties and JSON structure for the Card (new) visual in Power BI PBIR format.

## Overview

The Card visual displays a single aggregate value with optional category label,
callout formatting, and reference labels. Use visual type `card` (the modern
card, not the legacy `cardVisual`).

## Required Properties

| Property | Type | Description |
|---|---|---|
| `visual.visualType` | string | Must be `"card"` |
| `visual.query.queryState.Values.projections` | array | Exactly one field — the measure or column to display |

## Optional Properties

| Property | Type | Description |
|---|---|---|
| `visual.objects.calloutValue.properties.color` | color | Font color of the main value |
| `visual.objects.calloutValue.properties.fontSize` | int | Font size in pt (default 27) |
| `visual.objects.calloutValue.properties.fontFamily` | string | Font family |
| `visual.objects.calloutValue.properties.displayUnits` | int | Auto=0, None=1, K=2, M=3, B=4, T=5 |
| `visual.objects.calloutValue.properties.labelPrecision` | int | Decimal places |
| `visual.objects.categoryLabel.properties.show` | bool | Show/hide category label |
| `visual.objects.categoryLabel.properties.color` | color | Category label font color |
| `visual.objects.categoryLabel.properties.fontSize` | int | Category label font size |

## Minimal JSON Structure

```json
{
  "visual": {
    "visualType": "card",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "measure": {
                  "property": "Total Sales",
                  "expressionRef": { "source": { "entity": "Sales" } }
                }
              }
            }
          ]
        }
      }
    },
    "objects": {
      "calloutValue": [
        {
          "properties": {
            "fontSize": { "expr": { "Literal": { "Value": "27D" } } }
          }
        }
      ]
    }
  }
}
```

## Constraints

- Only one field in `Values` projections; the card shows a single value.
- Use `"card"` not `"cardVisual"` — the latter is the deprecated legacy card.
- `displayUnits` is an integer enum, not a string.
