import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useShallow } from "zustand/react/shallow";
import {
  createChatSession,
  expandChatInput,
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
import { Composer, type ComposerHandle } from "./Composer";

export function ChatPage({
  workspaceRoot,
}: {
  workspaceRoot: string | undefined;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [inputWarnings, setInputWarnings] = useState<string[]>([]);
  const composerRef = useRef<ComposerHandle>(null);

  const {
    liveSessionId,
    connection,
    inputEnabled,
    waitMessage,
    sessionUsage,
    turnUsage,
    sessionEnded,
    fatalError,
    items,
    subAgents,
  } = useChatStore(
    useShallow((s) => ({
      liveSessionId: s.liveSessionId,
      connection: s.connection,
      inputEnabled: s.inputEnabled,
      waitMessage: s.waitMessage,
      sessionUsage: s.sessionUsage,
      turnUsage: s.turnUsage,
      sessionEnded: s.sessionEnded,
      fatalError: s.fatalError,
      items: s.items,
      subAgents: s.subAgents,
    })),
  );

  const switchLiveSession = useChatStore((s) => s.switchLiveSession);
  const clearTimeline = useChatStore((s) => s.clearTimeline);

  const sessionsQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: fetchSessions,
    refetchInterval: 12_000,
  });

  const createSessionMutation = useMutation({
    mutationFn: createChatSession,
    onSuccess: (session) => switchLiveSession(session.live_session_id),
  });

  const sendInputMutation = useMutation({
    mutationFn: (payload: {
      text: string;
      file_paths: string[];
      image_paths: string[];
    }) => {
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
  const mutateRef = useRef(createSessionMutation.mutate);
  mutateRef.current = createSessionMutation.mutate;

  // Only open the WebSocket after the server has confirmed the session exists
  useLiveChatEvents(createSessionMutation.isSuccess ? liveSessionId : null);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    const resumeId = searchParams.get("session");
    if (resumeId) {
      mutateRef.current({ resume_session_id: resumeId });
      setSearchParams({}, { replace: true });
    } else {
      mutateRef.current(liveSessionId ? { live_session_id: liveSessionId } : {});
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Focus composer whenever input becomes available
  useEffect(() => {
    if (inputEnabled && liveSessionId && !sessionEnded) {
      composerRef.current?.focus();
    }
  }, [inputEnabled, liveSessionId, sessionEnded]);

  useEffect(() => {
    if (inputWarnings.length === 0) return undefined;
    const timeoutId = window.setTimeout(() => setInputWarnings([]), 5000);
    return () => window.clearTimeout(timeoutId);
  }, [inputWarnings]);

  const handleSubmit = async (text: string, imagePaths: string[]) => {
    setInputWarnings([]);
    const expanded = await expandChatInput(text);
    if (expanded.warnings.length > 0) {
      setInputWarnings(expanded.warnings);
    }

    const mergedImagePaths = Array.from(
      new Set([...expanded.image_paths, ...imagePaths]),
    );
    await sendInputMutation.mutateAsync({
      text: expanded.text,
      file_paths: expanded.file_paths,
      image_paths: mergedImagePaths,
    });
  };

  return (
    <section className={`chat-layout ${sidebarOpen ? "chat-layout--sidebar-open" : ""}`}>
      <div className={`sidebar ${sidebarOpen ? "sidebar--open" : ""}`}>
        <SessionSidebar
          sessions={sessionsQuery.data ?? []}
          isLoading={sessionsQuery.isLoading}
          activeSessionId={null}
          workspaceRoot={workspaceRoot}
          onNewSession={() => {
            createSessionMutation.mutate({});
            setSidebarOpen(false);
            setTimeout(() => composerRef.current?.focus(), 100);
          }}
          onResumeSession={(sessionId) =>
            createSessionMutation.mutate({ resume_session_id: sessionId })
          }
          onToggle={() => setSidebarOpen((prev) => !prev)}
          isOpen={sidebarOpen}
        />
      </div>

      <div className="chat-panel">
        <div className="chat-topbar">
          <ConnectionBadge connection={connection} />
          <UsageBar sessionUsage={sessionUsage} turnUsage={turnUsage} />
        </div>

        {inputWarnings.length > 0 ? (
          <div className="banner banner--notice">{inputWarnings.join(" ")}</div>
        ) : null}
        {fatalError ? <div className="banner banner--error">{fatalError}</div> : null}

        <ChatTimeline
          items={items}
          subAgents={subAgents}
          connection={connection}
        />

        <Composer
          ref={composerRef}
          inputEnabled={inputEnabled}
          sessionEnded={sessionEnded}
          liveSessionId={liveSessionId}
          waitMessage={waitMessage}
          onSubmit={handleSubmit}
        />
      </div>
    </section>
  );
}
