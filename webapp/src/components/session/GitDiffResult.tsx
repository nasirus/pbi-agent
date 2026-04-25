import {
  CheckCircle2Icon,
  FileCode2Icon,
  MinusIcon,
  PlusIcon,
  XCircleIcon,
} from "lucide-react";
import type { ApplyPatchToolMetadata } from "../../types";
import { Badge } from "../ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";

type DiffLineKind = "added" | "removed" | "context" | "hunk" | "meta" | "empty";

const EMPTY_DIFF_MESSAGE = "No diff content was provided for this operation.";

type DiffLine = {
  key: string;
  kind: DiffLineKind;
  text: string;
  oldNumber: number | null;
  newNumber: number | null;
};

type ParsedDiff = {
  lines: DiffLine[];
  added: number;
  removed: number;
  hunks: number;
};

const OPERATION_LABELS: Record<string, string> = {
  create_file: "Created",
  update_file: "Updated",
  delete_file: "Deleted",
};

export function isApplyPatchToolMetadata(
  metadata: ApplyPatchToolMetadata | undefined,
): metadata is ApplyPatchToolMetadata {
  return (
    metadata?.tool_name === "apply_patch" || Boolean(metadata?.diff && metadata.path)
  );
}

export function GitDiffResult({ metadata }: { metadata: ApplyPatchToolMetadata }) {
  const parsed = parseV4aDiff(metadata.diff ?? "", metadata.operation);
  const operationLabel =
    OPERATION_LABELS[metadata.operation ?? ""] ?? metadata.operation ?? "Edited";
  const statusLabel = metadata.success === false ? "Failed" : "Done";
  const visibleLines = parsed.lines.length > 0 ? parsed.lines : emptyStateLines();

  return (
    <Card
      size="sm"
      className="git-diff-result"
      data-status={metadata.success === false ? "failed" : "done"}
    >
      <CardHeader className="git-diff-result__header">
        <div className="git-diff-result__title-row">
          <span className="git-diff-result__file-icon" aria-hidden="true">
            <FileCode2Icon />
          </span>
          <div className="git-diff-result__title-copy">
            <CardTitle className="git-diff-result__title">
              {metadata.path ?? "Unknown file"}
            </CardTitle>
            <CardDescription className="git-diff-result__description">
              <span>{operationLabel}</span>
              {metadata.detail ? <span>{metadata.detail}</span> : null}
            </CardDescription>
          </div>
        </div>
        <CardAction className="git-diff-result__actions">
          <Badge
            variant={metadata.success === false ? "destructive" : "secondary"}
            className="git-diff-result__status"
          >
            {metadata.success === false ? (
              <XCircleIcon data-icon="inline-start" />
            ) : (
              <CheckCircle2Icon data-icon="inline-start" />
            )}
            {statusLabel}
          </Badge>
          <div className="git-diff-result__stats" aria-label="Diff summary">
            <Badge
              variant="outline"
              className="git-diff-result__stat git-diff-result__stat--added"
            >
              <PlusIcon data-icon="inline-start" />
              {parsed.added}
            </Badge>
            <Badge
              variant="outline"
              className="git-diff-result__stat git-diff-result__stat--removed"
            >
              <MinusIcon data-icon="inline-start" />
              {parsed.removed}
            </Badge>
          </div>
        </CardAction>
      </CardHeader>

      <CardContent className="git-diff-result__content">
        <div
          className="git-diff-result__viewport"
          role="region"
          aria-label={`Diff for ${metadata.path ?? "file"}`}
        >
          <table className="git-diff-result__table">
            <tbody>
              {visibleLines.map((line) => (
                <tr
                  key={line.key}
                  className={`git-diff-result__line git-diff-result__line--${line.kind}`}
                >
                  <td className="git-diff-result__gutter git-diff-result__gutter--old">
                    {line.oldNumber ?? ""}
                  </td>
                  <td className="git-diff-result__gutter git-diff-result__gutter--new">
                    {line.newNumber ?? ""}
                  </td>
                  <td className="git-diff-result__marker">{markerForLine(line.kind)}</td>
                  <td className="git-diff-result__code">
                    <code>{line.text || " "}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="git-diff-result__footer">
          <span>
            {parsed.hunks > 0
              ? `${parsed.hunks} hunk${parsed.hunks === 1 ? "" : "s"}`
              : "No diff hunks"}
          </span>
          {metadata.call_id ? (
            <Badge variant="ghost" className="git-diff-result__call-id">
              {metadata.call_id}
            </Badge>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

function parseV4aDiff(diff: string, operation: string | undefined): ParsedDiff {
  // The apply_patch tool uses V4A diffs rather than unified git patches. Map
  // those compact +/-/context lines into a git-diff-like view.
  const lines = diff.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  if (lines.length > 0 && lines.at(-1) === "") {
    lines.pop();
  }

  let oldNumber = 1;
  let newNumber = operation === "delete_file" ? 0 : 1;
  let added = 0;
  let removed = 0;
  let hunks = 0;

  const parsedLines: DiffLine[] = lines.map((rawLine, index) => {
    const key = `${index}-${rawLine}`;
    if (rawLine.startsWith("@@")) {
      hunks += 1;
      const anchor = rawLine.slice(2).trim();
      return {
        key,
        kind: "hunk",
        text: anchor || "Section",
        oldNumber: null,
        newNumber: null,
      };
    }
    if (rawLine.startsWith("***")) {
      return {
        key,
        kind: "meta",
        text: rawLine,
        oldNumber: null,
        newNumber: null,
      };
    }
    if (rawLine.startsWith("+")) {
      added += 1;
      const line: DiffLine = {
        key,
        kind: "added",
        text: rawLine.slice(1),
        oldNumber: null,
        newNumber: newNumber > 0 ? newNumber : null,
      };
      newNumber += 1;
      return line;
    }
    if (rawLine.startsWith("-")) {
      removed += 1;
      const line: DiffLine = {
        key,
        kind: "removed",
        text: rawLine.slice(1),
        oldNumber,
        newNumber: null,
      };
      oldNumber += 1;
      return line;
    }
    if (rawLine.startsWith(" ")) {
      const line: DiffLine = {
        key,
        kind: "context",
        text: rawLine.slice(1),
        oldNumber,
        newNumber: newNumber > 0 ? newNumber : null,
      };
      oldNumber += 1;
      newNumber += 1;
      return line;
    }
    return {
      key,
      kind: "empty",
      text: rawLine,
      oldNumber: null,
      newNumber: null,
    };
  });

  return { lines: parsedLines, added, removed, hunks };
}

function emptyStateLines(): DiffLine[] {
  return [
    {
      key: "empty",
      kind: "empty",
      text: EMPTY_DIFF_MESSAGE,
      oldNumber: null,
      newNumber: null,
    },
  ];
}

function markerForLine(kind: DiffLineKind): string {
  if (kind === "added") return "+";
  if (kind === "removed") return "-";
  if (kind === "hunk") return "@@";
  return "";
}
