# Skill Generator

Use this when the user asks to capture lessons learned after a task failed, was corrected, or revealed a non-obvious constraint — generates a new `.md` skill file so the same mistake is not repeated in future sessions.

## Failure Analysis

Review the full conversation and list every distinct mistake. For each one note:
- What was attempted — the action or output produced.
- Why it failed — the specific error, validation failure, or incorrect behavior.
- What fixed it — the corrected approach, property, structure, or constraint.

## Skill Scope And Naming

- One focused topic per skill file. Do not bundle unrelated lessons.
- Name with `snake_case` matching the topic (e.g., `line_chart_visual`, `composite_key_drillthrough`).
- Avoid generic names like `fixes` or `lessons`.
- If an existing skill already covers the topic, update it instead of creating a duplicate.

## Skill File Template

Every generated skill must follow this structure. The first non-heading line is the catalog brief — keep it under one sentence starting with "Use this when…".

```markdown
# <Skill Title>

Use this when <one-line: what scenario or task this skill applies to>.

## <Domain Rules / Structure Section>

<Numbered list of concrete, actionable rules. Each rule must be specific
enough to prevent the original mistake. No vague advice.>

1. <Rule>
2. <Rule>

## <Correct Pattern Section>

<Correct JSON skeleton, TMDL block, file layout, or code pattern.
Fenced code block with language tag. Inline comments where the mistake occurred.>

## Common Mistakes

- Do NOT <wrong approach> — instead <correct approach>.

## Constraints

<Hard constraints that must never be violated.>
```

## Where To Save

Save as `src/pbi_agent/skills/<skill_name>.md`. The loader auto-discovers all `.md` files — no code changes required.

## Verification Checklist

1. File exists at `src/pbi_agent/skills/<skill_name>.md`.
2. First non-heading line is a clear "Use this when…" brief.
3. Content is self-contained — a future session with no memory of this conversation can follow it.
4. References exact property names, paths, or syntax — not abstract guidance.
5. The correct pattern was verified to work during this conversation.

## Example Output

For a session where `"lineChart"` was used instead of `"lineClusteredColumnComboChart"` and Y-axis fields were placed under `Values` instead of `Y`:

```markdown
# Line Clustered Column Combo Chart

Use this when creating a combined line and bar chart in PBIR — Power BI uses the combo visual type, not a standalone line chart.

## Query Role Bindings

1. Set `visualType` to `"lineClusteredColumnComboChart"`, never `"lineChart"`.
2. Bind column series to the `"Y"` query role, not `"Values"`.
3. Bind line series to the `"Y2"` query role.
4. Category axis uses the `"Category"` query role.

## Correct Structure

\```json
{
  "visual": {
    "visualType": "lineClusteredColumnComboChart",
    "query": {
      "queryState": {
        "Category": { "projections": [...] },
        "Y":        { "projections": [...] },
        "Y2":       { "projections": [...] }
      }
    }
  }
}
\```

## Common Mistakes

- Do NOT use `"lineChart"` — not a valid PBIR visual type for combo scenarios.
- Do NOT place line measures under `"Y"` — use `"Y2"` for line series.

## Constraints

- `queryState` role keys are case-sensitive and must match exactly.
- Every projection must have both `queryRef` and `nativeQueryRef`.
```
