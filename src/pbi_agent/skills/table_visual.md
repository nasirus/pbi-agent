# Table Visual

Use PBIR table patterns with `tableEx`, projection ordering, deterministic sort, and high-contrast styling.

## Required Structure

- `visual.visualType` must be `"tableEx"`.
- Bind fields in `visual.query.queryState.Values.projections`.
- Use exact query casing (`Measure`/`Column`/`Expression`/`SourceRef`/`Property`).
- Optional: `query.sortDefinition` for deterministic ordering.

## Recommended Pattern

- Include stable business keys early in projection order.
- Add measures and descriptive columns after keys.
- Use explicit sort on key/date/priority metric.
- Style via:
  - `objects.columnHeaders` (`backColor`, `fontColor`)
  - `objects.grid` (`outlineColor`)
  - `visualContainerObjects` (`background`, `border`, `dropShadow`)

## Default Styling Pattern if no instructions given

- Header contrast:
  - `objects.columnHeaders.backColor` uses theme dark color (often black).
  - `objects.columnHeaders.fontColor` uses theme light color (often white).
- Grid lines:
  - `objects.grid.outlineColor` uses dark neutral (`'#252423'`) or black (`'#000000'`) for clear row separation.
- Container framing:
  - `visualContainerObjects.background.show = true`
  - `visualContainerObjects.background.transparency = 0D`
  - `visualContainerObjects.border.show = true`
  - `visualContainerObjects.border.radius = 5D`
  - `visualContainerObjects.border.width = 2D`
  - Border color can follow brand accent (`'#B6975A'`)
- Shadow:
  - Tables in the example use `visualContainerObjects.dropShadow.show = true`
  - Use `dropShadow.preset = 'Center'` for subtle depth

## UX/UI Guidance

- Keep a predictable scan path:
  - Key identifiers first
  - Status columns next
  - Numeric measures grouped together
- Keep the same column order across related pages to reduce user relearning.
- Avoid excessive column count on operational pages; split into focused tables when needed.
- Use strong header contrast and moderate grid contrast so dense tables stay readable.
- Keep table border radius aligned with card/slicer radius for a coherent page style.

## Minimal PBIR Skeleton

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
                  "Expression": { "SourceRef": { "Entity": "<dimension_table>" } },
                  "Property": "<key_column>"
                }
              },
              "queryRef": "<dimension_table>.<key_column>"
            },
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "<measure_table>" } },
                  "Property": "<measure_name>"
                }
              },
              "queryRef": "<measure_table>.<measure_name>"
            }
          ]
        }
      },
      "sortDefinition": {
        "sort": [
          {
            "field": {
              "Column": {
                "Expression": { "SourceRef": { "Entity": "<dimension_table>" } },
                "Property": "<sort_column>"
              }
            },
            "direction": "Descending"
          }
        ]
      }
    }
  }
}
```

## Constraints

- Keep projection order stable; this controls visible column order.
- Do not switch to legacy `table` visual type.
- Keep sort/filter definitions aligned with projected fields.
- If used on drillthrough pages, verify required drillthrough keys are included and visible (or intentionally hidden via formatting).
