import { useState, type JSX, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import type { TimelineItem } from "../../types";

function renderUserMessage(
  content: string,
  filePaths: string[] | undefined,
): JSX.Element {
  if (!filePaths || filePaths.length === 0) {
    return <p>{content}</p>;
  }

  const uniquePaths = Array.from(new Set(filePaths)).sort(
    (left, right) => right.length - left.length,
  );
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let partIndex = 0;

  while (cursor < content.length) {
    let nextMatch:
      | {
          index: number;
          path: string;
        }
      | undefined;

    for (const path of uniquePaths) {
      const index = content.indexOf(path, cursor);
      if (index < 0) {
        continue;
      }
      if (
        !nextMatch ||
        index < nextMatch.index ||
        (index === nextMatch.index && path.length > nextMatch.path.length)
      ) {
        nextMatch = { index, path };
      }
    }

    if (!nextMatch) {
      nodes.push(content.slice(cursor));
      break;
    }

    if (nextMatch.index > cursor) {
      nodes.push(content.slice(cursor, nextMatch.index));
    }
    nodes.push(
      <span
        key={`file-tag-${partIndex}`}
        className="timeline-entry__file-tag"
      >
        {nextMatch.path}
      </span>,
    );
    partIndex += 1;
    cursor = nextMatch.index + nextMatch.path.length;
  }

  return <p>{nodes}</p>;
}

export function TimelineEntry({
  item,
  subAgentTitle,
  subAgentStatus,
}: {
  item: TimelineItem;
  subAgentTitle?: string;
  subAgentStatus?: string;
}) {
  const [collapsed, setCollapsed] = useState(true);

  const subAgentBanner =
    subAgentTitle || subAgentStatus ? (
      <div className="timeline-entry__subagent">
        <span className={`indicator-dot indicator-dot--${subAgentStatus === "running" ? "connecting" : "connected"}`} />
        <span>{subAgentTitle ?? "sub_agent"} &middot; {subAgentStatus ?? "running"}</span>
      </div>
    ) : null;

  if (item.kind === "message") {
    const roleClass =
      item.role === "user" ? "user"
      : item.role === "error" ? "error"
      : item.role === "notice" ? "notice"
      : item.role === "debug" ? "debug"
      : "assistant";

    return (
      <div className={`timeline-entry timeline-entry--${roleClass}`}>
        {subAgentBanner}
        <div className="timeline-entry__content">
          {item.markdown && roleClass !== "user" ? (
            <ReactMarkdown>{item.content}</ReactMarkdown>
          ) : (
            renderUserMessage(
              item.content,
              item.kind === "message" && item.role === "user"
                ? item.filePaths
                : undefined,
            )
          )}
        </div>
      </div>
    );
  }

  if (item.kind === "thinking") {
    return (
      <div className="timeline-entry timeline-entry--thinking">
        {subAgentBanner}
        <div
          className="timeline-entry__header"
          onClick={() => setCollapsed((prev) => !prev)}
        >
          <span className={`timeline-entry__chevron ${collapsed ? "" : "timeline-entry__chevron--open"}`}>
            &#9654;
          </span>
          <span>{item.title}</span>
        </div>
        {!collapsed ? (
          <div className="timeline-entry__body">
            <ReactMarkdown>{item.content}</ReactMarkdown>
          </div>
        ) : null}
      </div>
    );
  }

  // tool_group
  return (
    <div className="timeline-entry timeline-entry--tool">
      {subAgentBanner}
      <div
        className="timeline-entry__header"
        onClick={() => setCollapsed((prev) => !prev)}
      >
        <span className={`timeline-entry__chevron ${collapsed ? "" : "timeline-entry__chevron--open"}`}>
          &#9654;
        </span>
        <span>{item.label}</span>
        <span className="timeline-entry__count">{item.items.length}</span>
      </div>
      {!collapsed ? (
        <div className="timeline-entry__body">
          {item.items.map((toolItem, index) => (
            <pre key={`${item.itemId}-${index}`} className="timeline-entry__tool-item">
              {toolItem.text}
            </pre>
          ))}
        </div>
      ) : null}
    </div>
  );
}
