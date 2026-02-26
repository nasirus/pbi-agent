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
  "$schema": "visual_container_schema_skill",
  "name": "cccccccccccccccccccc",
  "position": {
    "x": 20,
    "y": 240,
    "z": 20,
    "height": 460,
    "width": 1240
  },
  "visual": {
    "visualType": "clusteredBarChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            {
              "field": {
                "Column": {
                  "Expression": {
                    "SourceRef": {
                      "Entity": "TableName"
                    }
                  },
                  "Property": "CategoryColumn"
                }
              },
              "queryRef": "TableName.CategoryColumn",
              "nativeQueryRef": "CategoryColumn",
              "active": true
            }
          ]
        },
        "Y": {
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
      },
      "sortDefinition": {
        "sort": [
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
            "direction": "Descending"
          }
        ]
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
                    "Literal": {
                      "Value": "'#0E7490'"
                    }
                  }
                }
              }
            }
          },
          "selector": {
            "metadata": "MeasuresTable.MeasureName"
          }
        }
      ],
      "labels": [
        {
          "properties": {
            "show": {
              "expr": {
                "Literal": {
                  "Value": "true"
                }
              }
            },
            "detailLabelPrecision": {
              "expr": {
                "Literal": {
                  "Value": "0L"
                }
              }
            }
          }
        }
      ],
      "valueAxis": [
        {
          "properties": {
            "showAxisTitle": {
              "expr": {
                "Literal": {
                  "Value": "false"
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
                  "Value": "true"
                }
              }
            },
            "text": {
              "expr": {
                "Literal": {
                  "Value": "'Measure by Category'"
                }
              }
            },
            "fontSize": {
              "expr": {
                "Literal": {
                  "Value": "12D"
                }
              }
            },
            "alignment": {
              "expr": {
                "Literal": {
                  "Value": "'center'"
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

- Keep PBIR field node casing exact (`Measure`, `Column`, `Expression`, `SourceRef`, `Property`).
- Keep `queryRef` aligned with projected fields.
- In stacked/100% stacked charts, use consistent series ordering across related pages.
- Prefer selector-scoped formatting over global formatting when multiple measures are shown.
