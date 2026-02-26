# Visual Container Schema

Each visual container JSON file defines one visual **or** one visual group on a page.

## Top-Level Properties

| Property | Type | Required | Description |
|---|---|---|---|
| `$schema` | string | **yes** | Schema URI |
| `name` | string (max 50) | **yes** | Unique ID for the visual on this page |
| `position` | Position | **yes** | Location, size, and stacking order |
| `visual` | object | one of† | Chart/visual configuration (see `visualConfiguration` schema) |
| `visualGroup` | VisualGroup | one of† | Grouping container |
| `parentGroupName` | string | no | Name of parent group, if nested |
| `filterConfig` | object | no | Visual-level filters (on top of report/page filters) |
| `isHidden` | boolean | no | Hide the visual |
| `annotations` | Annotation[] | no | Metadata key/value pairs |

† Exactly one of `visual` or `visualGroup` must be present.

## Position

Required fields: `x`, `y`, `width`, `height` (all numbers).

| Field | Description |
|---|---|
| `x` | Left edge (0 → page width) |
| `y` | Top edge (0 → page height) |
| `z` | Stacking order (higher = on top) |
| `width` | Visual width (`x + width` ≤ page width) |
| `height` | Visual height (`y + height` ≤ page height) |
| `tabOrder` | Keyboard-navigation order |
| `angle` | Rotation angle |

## Visual Group

Required: `displayName` (string), `groupMode`.

| `groupMode` | Behaviour |
|---|---|
| `ScaleMode` | Children scale with group; preserves aspect ratio |
| `ScrollMode` | Children keep size; scrollbar added when overflowing |

Optional `objects` for group formatting: `background`, `lockAspect`, `general`.
Each is an array of `{ selector?, properties }` entries.

## Annotation

```json
{ "name": "<unique-key>", "value": "<string-value>" }
```

Both fields required.
