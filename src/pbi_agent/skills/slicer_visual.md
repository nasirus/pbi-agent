# Slicer Visual

Use `slicer` visual patterns with synced filters (`syncGroup`), clear container styling, and either date-range or dropdown interaction.

## Required Structure

- `visual.visualType = "slicer"`.
- Bind one field in `visual.query.queryState.Values.projections`.
- Optional `query.sortDefinition` for date fields.
- Add `syncGroup` so filters stay consistent across hidden/visible pages.
- `syncGroup.groupName` must represent one field only. Do not reuse same group name for different fields.

## Common Modes

- Date range slicer: `objects.data.properties.mode = 'Between'`.
- Dropdown slicer: `objects.data.properties.mode = 'Dropdown'`.
- For dropdown interaction pages, use `objects.general.properties.selfFilterEnabled = true` when self-filtering is required.

## Default Styling Pattern if no instructions given

- Header and mode:
  - `objects.header.show = false` in most pages for a cleaner filter row.
  - Date slicers use `mode = 'Between'`.
  - Entity/system slicers use `mode = 'Dropdown'`.
- Date slider color:
  - `objects.slider.color` uses brand accent (`'#B6975A'`) in Between mode.
- Container style baseline:
  - `visualContainerObjects.background.show = true`
  - `visualContainerObjects.background.transparency = 0D` (or `50D` for lighter overlays)
  - `visualContainerObjects.border.radius = 5D`
  - `visualContainerObjects.border.width = 1D` (sometimes `2D` on framed pages)
  - Keep `border.show = false` by default; enable for dedicated filter panels.
  - Keep `dropShadow.show = false` by default; enable only when slicer must read as a floating filter card.
- Sync groups found in the model:
  - Date groups: `date_id`, `date_id1`, `date_id2`
  - Entity groups: `site_name`, `system_label`

## UX/UI Guidance

- Keep filter order stable across pages (typically date, then site, then system).
- Keep slicer size/position consistent so users build muscle memory.
- Use one sync group per field and reuse it globally to avoid filter drift.
- For Between slicers, optional `startDate`/`endDate` can set intentional default windows.
- For long dropdown lists, keep slicer width sufficient and prefer searchable dropdown behavior.

## Minimal Date Slicer Skeleton

```json
{
  "visual": {
    "visualType": "slicer",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "<date_table>" } },
                  "Property": "<date_column>"
                }
              },
              "queryRef": "<date_table>.<date_column>"
            }
          ]
        }
      }
    },
    "objects": {
      "data": [{ "properties": { "mode": { "expr": { "Literal": { "Value": "'Between'" } } } } }]
    },
    "syncGroup": {
      "groupName": "date_main",
      "fieldChanges": true,
      "filterChanges": true
    }
  }
}
```

## How To Synchronize Multiple Filters Across Pages

1. Add slicers on each participating page for the same fields (date/site/system).
2. Use identical `syncGroup.groupName` per field on every participating page.
3. Keep projection field expression identical (`Entity` + `Property`) across those pages.
4. Keep `fieldChanges: true` and `filterChanges: true`.
5. Verify by changing one slicer and confirming all pages open with same selection.
6. Do not mix legacy and new group names unless you intentionally want isolated behavior.

## Constraint

- Reuse existing `syncGroup.groupName` when editing an existing cross-page filter; creating a new group breaks synchronization.
