import { useEffect, useRef } from "react";
import { useAutoScroll } from "../../hooks/useAutoScroll";
import type { TimelineItem } from "../../types";
import { EmptyState } from "../shared/EmptyState";
import { TimelineEntry } from "./TimelineEntry";

const USER_MESSAGE_TOP_OFFSET = 8;

export function ChatTimeline({
  items,
  subAgents,
  connection,
}: {
  items: TimelineItem[];
  subAgents: Record<string, { title: string; status: string }>;
  connection: "disconnected" | "connecting" | "connected";
}) {
  const previousLengthRef = useRef<number>();
  const latestItem = items.at(-1);
  const latestItemIsUserMessage =
    latestItem?.kind === "message" && latestItem.role === "user";
  const { containerRef, showNewMessages, scrollToBottom } = useAutoScroll(
    [items.length],
    { followOnChange: !latestItemIsUserMessage },
  );

  useEffect(() => {
    const previousLength = previousLengthRef.current;
    previousLengthRef.current = items.length;
    if (previousLength === undefined || items.length <= previousLength) {
      return;
    }
    if (!latestItemIsUserMessage || !latestItem) {
      return;
    }

    const container = containerRef.current;
    if (!container) {
      return;
    }

    const target = container.querySelector<HTMLElement>(
      `[data-timeline-item-id="${CSS.escape(latestItem.itemId)}"]`,
    );
    if (!target) {
      return;
    }

    container.scrollTo({
      top: Math.max(target.offsetTop - USER_MESSAGE_TOP_OFFSET, 0),
      behavior: "smooth",
    });
  }, [containerRef, items.length, latestItem, latestItemIsUserMessage]);

  if (items.length === 0 && connection === "connected") {
    return (
      <div className="timeline" ref={containerRef}>
        <EmptyState
          title="No messages yet"
          description="Send a message to start the conversation"
        />
      </div>
    );
  }

  return (
    <div className="timeline" ref={containerRef}>
      {items.map((item) => (
        <TimelineEntry
          key={item.itemId}
          item={item}
          subAgentTitle={item.subAgentId ? subAgents[item.subAgentId]?.title : undefined}
          subAgentStatus={item.subAgentId ? subAgents[item.subAgentId]?.status : undefined}
        />
      ))}
      {showNewMessages ? (
        <button
          type="button"
          className="timeline__new-messages"
          onClick={scrollToBottom}
        >
          New messages below
        </button>
      ) : null}
    </div>
  );
}
