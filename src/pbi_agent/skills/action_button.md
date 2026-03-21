# Action Button

Use this for implementing buttons that trigger navigation, drillthrough, bookmarks, or other linked actions.

## Minimal Skeleton

```json
{
  "$schema": "visual_container_schema_skill",
  "name": "2904fe3e965b23414593",
  "position": {
    "x": 91,
    "y": 8,
    "z": 4000,
    "height": 32,
    "width": 112,
    "tabOrder": 1000
  },
  "visual": {
    "visualType": "actionButton",
    "objects": {
      "icon": [
        {
          "properties": {
            "shapeType": {
              "expr": {
                "Literal": {
                  "Value": "'leftArrow'"
                }
              }
            },
            "topMargin": {
              "expr": {
                "Literal": {
                  "Value": "10L"
                }
              }
            },
            "bottomMargin": {
              "expr": {
                "Literal": {
                  "Value": "10L"
                }
              }
            }
          },
          "selector": {
            "id": "default"
          }
        }
      ],
      "text": [
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
        },
        {
          "properties": {
            "text": {
              "expr": {
                "Literal": {
                  "Value": "'PREVIOUS PAGE'"
                }
              }
            },
            "leftMargin": {
              "expr": {
                "Literal": {
                  "Value": "30L"
                }
              }
            },
            "horizontalAlignment": {
              "expr": {
                "Literal": {
                  "Value": "'left'"
                }
              }
            },
            "fontSize": {
              "expr": {
                "Literal": {
                  "Value": "8D"
                }
              }
            }
          },
          "selector": {
            "id": "default"
          }
        }
      ]
    },
    "visualContainerObjects": {
      "visualLink": [
        {
          "properties": {
            "show": {
              "expr": {
                "Literal": {
                  "Value": "true"
                }
              }
            },
            "type": {
              "expr": {
                "Literal": {
                  "Value": "'Back'"
                }
              }
            }
          }
        }
      ],
      "title": [
        {
          "properties": {
            "text": {
              "expr": {
                "Literal": {
                  "Value": "'Btn - Previous Page'"
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