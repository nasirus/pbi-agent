# Table Visual

Use this when creating or editing PBIR `tableEx` visuals.

## Required Structure

1. Set `visual.visualType` to `"tableEx"`.
2. Bind fields in `visual.query.queryState.Values.projections` using exact PBIR casing: `Measure` / `Column` / `Expression` / `SourceRef` / `Property`.
3. Keep `queryRef` equal to the exact semantic-model reference, for example `entityA.Name`.
4. Give every projection a unique `nativeQueryRef` within the same visual.
5. When multiple projected fields share the same property name across different entities, never reuse the raw property name for all `nativeQueryRef` values.

## Query Projection Rules

1. Projection order controls visible column order; place the most important identifiers, dates, or labels first.
2. Add explicit `query.sortDefinition` for deterministic ordering.
3. If multiple entities expose the same property name, alias the `nativeQueryRef` values to stable, entity-specific names.
4. Keep friendly labels in `displayName`; use `nativeQueryRef` only as the internal unique select-clause alias.
5. Before finalizing a table visual, scan all projections and confirm no `nativeQueryRef` value appears more than once.

## Default Styling Pattern if no instructions given

1. Keep the standard table design guidance from the base skill.
2. Use high-contrast headers:
   - `objects.columnHeaders.backColor` uses the theme dark color.
   - `objects.columnHeaders.fontColor` uses the theme light color.
3. Use clear grid separation:
   - `objects.grid.outlineColor` uses a dark neutral or black.
4. Keep card-like container framing:
   - `visualContainerObjects.background.show = true`
   - `visualContainerObjects.background.transparency = 0D`
   - `visualContainerObjects.border.show = true`
   - `visualContainerObjects.border.radius = 5D`
   - `visualContainerObjects.border.width = 1D` or `2D` depending on the page style
5. Use subtle depth when consistent with the page:
   - `visualContainerObjects.dropShadow.show = true`
   - `visualContainerObjects.dropShadow.preset = "Center"`
6. Keep the table border radius aligned with cards and slicers on the same page.

## Correct Pattern

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
                  "Expression": { "SourceRef": { "Entity": "entityA" } },
                  "Property": "Name"
                }
              },
              "queryRef": "entityA.Name",
              "nativeQueryRef": "EntityAName",
              "displayName": "Entity A Name"
            },
            {
              "field": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "entityB" } },
                  "Property": "Name"
                }
              },
              "queryRef": "entityB.Name",
              "nativeQueryRef": "EntityBName",
              "displayName": "Entity B Name"
            }
          ]
        }
      },
      "sortDefinition": {
        "sort": [
          {
            "field": {
              "Column": {
                "Expression": { "SourceRef": { "Entity": "factTable" } },
                "Property": "Date"
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

## Common Mistakes

- Do NOT project `entityA.Name` and `entityB.Name` with the same `nativeQueryRef: "Name"` — use unique aliases such as `EntityAName` and `EntityBName`.
- Do NOT assume `queryRef` uniqueness is enough — Power BI also requires unique select-clause native references.
- Do NOT change `queryRef` just to make aliases unique — keep `queryRef` bound to the real model field and change only `nativeQueryRef` / `displayName`.

## Constraints

- `nativeQueryRef` values must be unique per visual query.
- `queryRef` must remain aligned to the actual entity and property names in the semantic model.
- Keep sort and filter definitions aligned with projected fields after any alias change.
- If the table is used on a drillthrough page, preserve the required business fields and drillthrough keys while fixing aliases.
