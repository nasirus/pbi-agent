import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  createChatSession,
  fetchSessions,
  requestNewChat,
  submitChatInput,
} from "../../api";
import { useChatStore } from "../../store";
import { useLiveChatEvents } from "../../hooks/useLiveChatEvents";
import { ConnectionBadge } from "./ConnectionBadge";
import { SessionSidebar } from "./SessionSidebar";
import { ChatTimeline } from "./ChatTimeline";
import { UsageBar } from "./UsageBar";
import { Composer } from "./Composer";

export function ChatPage({
  workspaceRoot,
}: {
  workspaceRoot: string | undefined;
}): JSX.Element {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const liveSessionId = useChatStore((s) => s.liveSessionId);
  const switchLiveSession = useChatStore((s) => s.switchLiveSession);
  const clearTimeline = useChatStore((s) => s.clearTimeline);
  const connection = useChatStore((s) => s.connection);
  const inputEnabled = useChatStore((s) => s.inputEnabled);
  const waitMessage = useChatStore((s) => s.waitMessage);
  const sessionUsage = useChatStore((s) => s.sessionUsage);
  const turnUsage = useChatStore((s) => s.turnUsage);
  const sessionEnded = useChatStore((s) => s.sessionEnded);
  const fatalError = useChatStore((s) => s.fatalError);
  const items = useChatStore((s) => s.items);
  const subAgents = useChatStore((s) => s.subAgents);

  const sessionsQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: fetchSessions,
    refetchInterval: 12000,
  });

  const createSessionMutation = useMutation({
    mutationFn: createChatSession,
    onSuccess: (session) => switchLiveSession(session.live_session_id),
  });

  const sendInputMutation = useMutation({
    mutationFn: (payload: { text: string; image_paths: string[] }) => {
      if (!liveSessionId) throw new Error("No live session available.");
      return submitChatInput(liveSessionId, payload);
    },
  });

  const newChatMutation = useMutation({
    mutationFn: () => {
      if (!liveSessionId) throw new Error("No live session available.");
      return requestNewChat(liveSessionId);
    },
    onSuccess: () => clearTimeline(),
  });

  const startedRef = useRef(false);
  useLiveChatEvents(liveSessionId);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    createSessionMutation.mutate(
      liveSessionId ? { live_session_id: liveSessionId } : {},
    );
  }, [createSessionMutation, liveSessionId]);

  const handleSubmit = async (text: string, imagePaths: string[]) => {
    await sendInputMutation.mutateAsync({ text, image_paths: imagePaths });
  };

  return (
    <section className={`chat-layout ${sidebarOpen ? "chat-layout--sidebar-open" : ""}`}>
      <div className={`sidebar ${sidebarOpen ? "sidebar--open" : ""}`}>
        <SessionSidebar
          sessions={sessionsQuery.data ?? []}
          isLoading={sessionsQuery.isLoading}
          activeSessionId={null}
          workspaceRoot={workspaceRoot}
          onNewSession={() => createSessionMutation.mutate({})}
          onResumeSession={(sessionId) =>
            createSessionMutation.mutate({ resume_session_id: sessionId })
          }
          onToggle={() => setSidebarOpen((prev) => !prev)}
          isOpen={sidebarOpen}
        />
      </div>

      <div className="chat-panel">
        <ConnectionBadge connection={connection} />

        {waitMessage ? <div className="banner banner--wait">{waitMessage}</div> : null}
        {fatalError ? <div className="banner banner--error">{fatalError}</div> : null}

        <ChatTimeline
          items={items}
          subAgents={subAgents}
          connection={connection}
        />

        <UsageBar sessionUsage={sessionUsage} turnUsage={turnUsage} />

        <Composer
          inputEnabled={inputEnabled}
          sessionEnded={sessionEnded}
          liveSessionId={liveSessionId}
          onSubmit={handleSubmit}
        />
      </div>
    </section>
  );
}
