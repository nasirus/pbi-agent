# Card Visual

Use PBIR card patterns (`cardVisual` and `card`) with query-correct bindings and deliberate visual styling.

## Visual Type Choice

- Use `"cardVisual"` when editing legacy/multi-tile cards.
- Use `"card"` for modern single-value cards.
- Do not switch type in-place unless you migrate the full object/query schema.

## Required Structure

- For `cardVisual`:
  - `visual.query.queryState.Data.projections`.
  - Optional multi-field tiles with `selector.metadata` formatting.
- For `card`:
  - `visual.query.queryState.Values.projections`.
  - Single primary callout value.
- Keep query expression casing exact: `Measure`/`Column`/`Expression`/`SourceRef`/`Property`.

## Common Object Blocks (`cardVisual`)

- `layout`: orientation, alignment, tile behavior.
- `label`: text, placement, font, per-field override.
- `value`: font size/color/alignment, per-field override.
- `accentBar`: status-color strip per field.
- `padding`, `spacing`, `outline`, `shapeCustomRectangle`.
- `fillCustom`: conditional color fill from a color column/measure.
- `visualContainerObjects`: `title`, `background`, `border`, `dropShadow`.

## Default Styling Pattern if no instructions given

- Rounded tile style:
  - `objects.shapeCustomRectangle.rectangleRoundedCurve` is typically `5L` or `6L`.
  - In compact cards, `objects.layout.rectangleRoundedCurve` can stay `0L` while shape controls rounding.
- Border and container:
  - `visualContainerObjects.border.radius = 5D`
  - `visualContainerObjects.border.width = 1D` or `2D`
  - Border color often uses brand gold (`'#B6975A'`)
- Background and depth:
  - Use `visualContainerObjects.background.show = true` for framed cards.
  - Use `background.transparency = 0D` (solid) or `50D` (lighter overlays).
  - Keep `dropShadow.show = false` by default; enable only for emphasis cards.
  - When shadow config exists, keep it subtle: `preset = 'Center'`, `transparency = 70L`.
- Typography and spacing:
  - Label often around `8D` to `11D`.
  - Value often around `12D` and semibold family from theme.
  - Theme baseline uses `paddingUniform = 12` and `verticalSpacing = 2`.
- Conditional status coloring:
  - `objects.fillCustom.fillColor` can use an `Aggregation` expression to bind a color code column.
  - Use this for KPI state cards (OK/warning/critical) instead of static color duplication.

## UX/UI Guidance

- Keep card density controlled (theme pattern uses `maxTiles = 3`).
- Use one visual hierarchy per row:
  - Primary KPI cards (largest)
  - Secondary KPI cards
  - Indicator chips/color tiles
- Keep card states consistent:
  - Same rounding, same border logic, same meaning per color.
- If a card is purely a status indicator, hide value/label intentionally and rely on fill + tooltip.
- Enable either title or categoryLabels, but not both, to avoid redundant text (prefer categoryLabels by default).
## Minimal PBIR Skeleton

```json
{
  "$schema": "visual_container_schema_skill",
  "name": "55555555555555555555",
  "position": {
    "x": 844,
    "y": 20,
    "z": 5,
    "height": 85,
    "width": 196
  },
  "visual": {
    "visualType": "card",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "Measure": {
                  "Expression": {
                    "SourceRef": {
                      "Entity": "MeasuresTable"
                    }
                  },
                  "Property": "MeasureName"
                }
              },
              "queryRef": "MeasuresTable.MeasureName",
              "nativeQueryRef": "MeasureName"
            }
          ]
        }
      }
    },
    "objects": {
      "categoryLabels": [
        {
          "properties": {
            "show": {
              "expr": {
                "Literal": {
                  "Value": "true"
                }
              }
            }
          }
        }
      ]
    },
    "visualContainerObjects": {
      "title": [
        {
          "properties": {
            "show": {
              "expr": {
                "Literal": {
                  "Value": "false"
                }
              }
            },
            "text": {
              "expr": {
                "Literal": {
                  "Value": "'Measure Name'"
                }
              }
            }
          }
        }
      ],
      "background": [
        {
          "properties": {
            "show": {
              "expr": {
                "Literal": {
                  "Value": "true"
                }
              }
            },
            "transparency": {
              "expr": {
                "Literal": {
                  "Value": "0D"
                }
              }
            }
          }
        }
      ],
      "border": [
        {
          "properties": {
            "show": {
              "expr": {
                "Literal": {
                  "Value": "true"
                }
              }
            },
            "radius": {
              "expr": {
                "Literal": {
                  "Value": "6D"
                }
              }
            },
            "width": {
              "expr": {
                "Literal": {
                  "Value": "1D"
                }
              }
            },
            "color": {
              "solid": {
                "color": {
                  "expr": {
                    "Literal": {
                      "Value": "'#C9D4E5'"
                    }
                  }
                }
              }
            }
          }
        }
      ],
      "dropShadow": [
        {
          "properties": {
            "show": {
              "expr": {
                "Literal": {
                  "Value": "true"
                }
              }
            },
            "preset": {
              "expr": {
                "Literal": {
                  "Value": "'Center'"
                }
              }
            },
            "transparency": {
              "expr": {
                "Literal": {
                  "Value": "80L"
                }
              }
            },
            "shadowBlur": {
              "expr": {
                "Literal": {
                  "Value": "10L"
                }
              }
            },
            "shadowSpread": {
              "expr": {
                "Literal": {
                  "Value": "1L"
                }
              }
            },
            "shadowDistance": {
              "expr": {
                "Literal": {
                  "Value": "0L"
                }
              }
            },
            "angle": {
              "expr": {
                "Literal": {
                  "Value": "0L"
                }
              }
            }
          }
        }
      ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

## Constraints

- Preserve `selector.metadata` in multi-field cards when editing formatting.
- Keep `queryRef` and `Property` names exact, including spaces/symbols.
- Use explicit formatting for status/threshold cards instead of relying only on theme defaults.
