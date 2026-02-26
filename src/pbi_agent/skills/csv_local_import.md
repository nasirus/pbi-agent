# Local CSV Import

Use this when creating or editing a PBIP semantic model that imports CSV data from a local file or local folder.

## Where CSV Source Is Defined In TMDL

- `definition/database.tmdl`: model compatibility only (no CSV path here).
- `definition/model.tmdl`: model metadata and `ref table ...` entries.
- `definition/expressions.tmdl` (recommended): path parameters (`csv_file_path`, `csv_folder_path`).
- `definition/tables/<table>.tmdl`: real data-source logic in `partition <table> = m` with M code.
- `definition/relationships.tmdl`: relationship graph after tables are loaded.

## Parameterize Local Paths (Recommended)

Avoid hardcoded absolute paths in `File.Contents("C:\\...")`. Create text parameters in `expressions.tmdl` and reuse them in partitions.

```tmdl
expression csv_file_path = "C:\\Data\\inbound\\sales.csv" meta [IsParameterQuery = true, IsParameterQueryRequired = true, Type = "Text"]

expression csv_folder_path = "C:\\Data\\inbound" meta [IsParameterQuery = true, IsParameterQueryRequired = true, Type = "Text"]
```

## Single CSV File Partition Template

```tmdl
partition fact_sales = m
	mode: import
	source =
			let
			    Source = Csv.Document(
			        File.Contents(csv_file_path),
			        [Delimiter=",", Columns=4, Encoding=65001, QuoteStyle=QuoteStyle.Csv]
			    ),
			    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
			    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
			        {"order_id", Int64.Type},
			        {"order_date", type date},
			        {"amount", type number},
			        {"customer", type text}
			    })
			in
			    #"Changed Type"

annotation PBI_ResultType = Table
```

## Local Folder (Multi-CSV) Partition Template

Use this when the source is a folder with many CSV files sharing the same schema.

```tmdl
partition fact_sales = m
	mode: import
	source =
			let
			    Source = Folder.Files(csv_folder_path),
			    #"Keep CSV" = Table.SelectRows(Source, each Text.Lower([Extension]) = ".csv"),
			    #"Parsed Tables" = List.Transform(#"Keep CSV"[Content], each Table.PromoteHeaders(Csv.Document(_, [Delimiter=",", Columns=4, Encoding=65001, QuoteStyle=QuoteStyle.Csv]), [PromoteAllScalars=true])),
			    #"Combined Data" = Table.Combine(#"Parsed Tables"),
			    #"Changed Type" = Table.TransformColumnTypes(#"Combined Data",{
			        {"order_id", Int64.Type},
			        {"order_date", type date},
			        {"amount", type number},
			        {"customer", type text}
			    })
			in
			    #"Changed Type"
```

## Column And Model Definition Rules

- Declare each model column in the table TMDL with explicit `dataType`, `summarizeBy`, and `sourceColumn`.
- Keep source-to-model names stable; report bindings rely on exact field names.
- Set `formatString` explicitly for numeric/date business fields.
- Add date variations/relationships only when date hierarchy UX is needed.

## CSV Import Validation Checklist

1. Confirm delimiter, encoding, quote style, and expected column count match real files.
2. Confirm every referenced column exists after header promotion.
3. Confirm local path exists on the refresh machine (not only developer machine).
4. Confirm model column types match M `Table.TransformColumnTypes`.
5. Confirm relationships still validate after refresh (`relationships.tmdl` keys and datatypes).

## Common Failure Modes

- Wrong delimiter or encoding: columns shift or mojibake appears.
- Header row not promoted: `sourceColumn` mapping fails.
- Hardcoded user path: refresh fails on other machines.
- Folder import with mixed schemas: expand/type steps fail on some files.
- Local path in Service without gateway: scheduled refresh fails.
