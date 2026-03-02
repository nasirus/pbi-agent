# TMDL Descriptions

Use this when adding or editing descriptions for tables and columns in TMDL files (`*.tmdl`).

## Description Syntax

In TMDL, descriptions are added as triple-slash (`///`) comment lines **immediately above** the object declaration they describe. The description is not a regular comment — it becomes the object's `description` metadata in the semantic model.

## Adding a Column Description

Place a `/// <description text>` line directly above the `column` declaration, at the same indentation level:

```tmdl
table ShipmentData
	lineageTag: a8081e76-2aa9-43f4-8bee-1869c7e4561f

	/// Creation datetime of the ASN record
	column ASN_CREATION_DATETIME
		dataType: dateTime
		formatString: General Date
		lineageTag: 09c1021a-7b8e-4bf1-96fd-78aba2d1e3bc
		summarizeBy: none
		sourceColumn: ASN_CREATION_DATETIME
```

## Adding a Table Description

Place a `/// <description text>` line directly above the `table` declaration, with no indentation:

```tmdl
/// Shipment Data Table Description
table ShipmentData
	lineageTag: a8081e76-2aa9-43f4-8bee-1869c7e4561f

	column DOCUMENT_DATE
		dataType: dateTime
		formatString: Short Date
		lineageTag: d17d4325-8d0e-47fe-b2fd-caf888d49463
		summarizeBy: none
		sourceColumn: DOCUMENT_DATE
```

## Adding a Measure Description

The same pattern applies to measures:

```tmdl
	/// Total number of rows in the shipment table
	measure '# Shipments' = COUNTROWS(ShipmentData)
		formatString: 0
```

## Rules

- The `///` line must be placed **directly above** the object declaration (no blank lines between).
- Use the **same indentation** as the object being described (e.g., one tab for columns/measures inside a table, no indent for tables).
- Do not confuse `///` (description) with `//` (regular comment). Only `///` sets the object description metadata.
- Descriptions are visible in Power BI Desktop tooltips and documentation views.

## Checklist

- Place `///` directly above the target `table`, `column`, or `measure` line.
- Match the indentation of the object being described.
- Do not insert blank lines between the `///` line and the declaration.
- Use multi-line `///` for longer descriptions when needed.
