# Table Visual

Properties and JSON structure for the Table visual in Power BI PBIR format.

## Overview

The Table visual renders data as a flat grid of rows and columns. It supports
column-level formatting, totals, conditional formatting, and URL/image rendering.
Visual type is `tableEx`.

## Required Properties

| Property | Type | Description |
|---|---|---|
| `visual.visualType` | string | Must be `"tableEx"` |
| `visual.query.queryState.Values.projections` | array | One or more fields — each becomes a column |

## Optional Properties

| Property | Type | Description |
|---|---|---|
| `visual.objects.total.properties.totals` | bool | Show/hide grand total row |
| `visual.objects.total.properties.fontColor` | color | Total row font color |
| `visual.objects.total.properties.backColor` | color | Total row background |
| `visual.objects.values.properties.fontColor` | color | Data cell font color |
| `visual.objects.values.properties.backColor` | color | Data cell background |
| `visual.objects.values.properties.fontSize` | int | Data cell font size |
| `visual.objects.values.properties.urlIcon` | bool | Show URL values as clickable links |
| `visual.objects.columnHeaders.properties.fontColor` | color | Header font color |
| `visual.objects.columnHeaders.properties.fontSize` | int | Header font size |
| `visual.objects.columnHeaders.properties.bold` | bool | Bold headers |
| `visual.objects.grid.properties.gridVertical` | bool | Show vertical grid lines |
| `visual.objects.grid.properties.gridHorizontal` | bool | Show horizontal grid lines |
| `visual.objects.grid.properties.rowPadding` | int | Row padding in px |
| `visual.objects.columnFormatting[n].properties.wordWrap` | bool | Wrap text in column n |

## Conditional Formatting

Apply per-column rules via `visual.objects.values` scoped to a specific column
index. Use `"selector": {"data": [{"dataViewWildcard": {"matchingOption": 0}}]}`
for all rows in a column.

## Minimal JSON Structure

```json
{
  "visual": {
    "visualType": "tableEx",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "Column": {
                  "property": "Product",
                  "expressionRef": { "source": { "entity": "Products" } }
                }
              }
            },
            {
              "field": {
                "measure": {
                  "property": "Revenue",
                  "expressionRef": { "source": { "entity": "Sales" } }
                }
              }
            }
          ]
        }
      }
    },
    "objects": {
      "total": [
        {
          "properties": {
            "totals": { "expr": { "Literal": { "Value": "true" } } }
          }
        }
      ],
      "columnHeaders": [
        {
          "properties": {
            "bold": { "expr": { "Literal": { "Value": "true" } } }
          }
        }
      ]
    }
  }
}
```

## Constraints

- Visual type is `"tableEx"`, not `"table"` (legacy).
- Column order matches the order of projections in the `Values` array.
- Conditional formatting rules reference columns by their query field index.
