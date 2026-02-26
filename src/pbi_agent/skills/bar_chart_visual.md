# Bar Chart Visual

Use PBIR bar-chart patterns with `Category` + `Y` roles, selector-scoped colors, and consistent container styling.

## Supported Visual Types

- `barChart`
- `clusteredBarChart`
- `stackedBarChart`
- `hundredPercentStackedBarChart`

## Required Query Shape

- `visual.visualType` set to one of the bar chart types.
- `visual.query.queryState.Category.projections`: at least one categorical field.
- `visual.query.queryState.Y.projections`: one or more measures.
- Optional: `visual.query.sortDefinition` for explicit sort behavior.
- Optional: `filterConfig.filters` for fixed-scope visual filtering.

## Common Object Blocks

- `valueAxis`: show/hide, axis title, display units.
- `categoryAxis`: label formatting and density control.
- `labels`: show/hide and precision.
- `dataPoint`: per-series color using `selector.metadata`.
- `legend`: position and visibility.
- `visualContainerObjects`: title/background/border/dropShadow.

## Default Styling Pattern if no instructions given

- Use card-like containers:
  - `visualContainerObjects.background.show = true`
  - `visualContainerObjects.background.transparency = 0D`
  - `visualContainerObjects.border.show = true`
  - `visualContainerObjects.border.radius = 5D` or `6D`
  - `visualContainerObjects.border.width = 1D`
- Keep shadows subtle:
  - Default `visualContainerObjects.dropShadow.show = false`
  - If used, keep it soft: `preset = 'Custom'`, `position = 'Outer'`, `shadowBlur = 15L`, `shadowSpread = 3L`, `transparency = 70L`
- Use selector-scoped status colors in `objects.dataPoint`:
  - Positive/OK often green (`'#109E42'`)
  - Negative/KO often red (`'#CB381B'`)
- Keep labels compact:
  - `objects.labels.show = true`
  - `objects.labels.detailLabelPrecision = 0L`
  - `objects.valueAxis.showAxisTitle = false` for dense dashboards

## UX/UI Guidance

- Keep category count reasonable (about 8 to 12) to avoid unreadable bars.
- Keep color semantics stable across pages (same color = same meaning everywhere).
- Hide legends when a chart has one obvious measure and label directly on bars.
- Reuse the same border radius/width used by cards and tables on the same page.

## Minimal PBIR Skeleton

```json
{
  "visual": {
    "visualType": "clusteredBarChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            {
              "field": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "<dimension_table>" } },
                  "Property": "<category_column>"
                }
              },
              "queryRef": "<dimension_table>.<category_column>"
            }
          ]
        },
        "Y": {
          "projections": [
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "<measure_table>" } },
                  "Property": "<measure_1>"
                }
              },
              "queryRef": "<measure_table>.<measure_1>"
            },
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "<measure_table>" } },
                  "Property": "<measure_2>"
                }
              },
              "queryRef": "<measure_table>.<measure_2>"
            }
          ]
        }
      }
    },
    "objects": {
      "dataPoint": [
        {
          "properties": {
            "fill": {
              "solid": {
                "color": {
                  "expr": {
                    "Literal": { "Value": "'#00AA55'" }
                  }
                }
              }
            }
          },
          "selector": { "metadata": "<measure_table>.<measure_1>" }
        }
      ]
    }
  }
}
```

## Constraints

- Keep PBIR field node casing exact (`Measure`, `Column`, `Expression`, `SourceRef`, `Property`).
- Keep `queryRef` aligned with projected fields.
- In stacked/100% stacked charts, use consistent series ordering across related pages.
- Prefer selector-scoped formatting over global formatting when multiple measures are shown.
