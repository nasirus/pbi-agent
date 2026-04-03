import { useEffect, useRef } from "react";
import { websocketUrl } from "../api";
import { useChatStore } from "../store";
import type { WebEvent } from "../types";

const INITIAL_DELAY = 1000;
const MAX_DELAY = 30000;

export function useLiveChatEvents(
  chatKey: string | null,
  liveSessionId: string | null,
): void {
  const applyEvent = useChatStore((state) => state.applyEvent);
  const setConnection = useChatStore((state) => state.setConnection);
  const retryDelay = useRef(INITIAL_DELAY);

  useEffect(() => {
    if (!chatKey || !liveSessionId) {
      if (chatKey) {
        setConnection(chatKey, "disconnected");
      }
      return;
    }
    const currentChatKey = chatKey;
    const currentLiveSessionId = liveSessionId;

    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    function connect() {
      if (disposed) return;
      setConnection(currentChatKey, "connecting");
      socket = new WebSocket(websocketUrl(`/api/events/${currentLiveSessionId}`));

      socket.onopen = () => {
        retryDelay.current = INITIAL_DELAY;
        setConnection(currentChatKey, "connected");
      };

      socket.onmessage = (message) => {
        if (typeof message.data !== "string") {
          return;
        }
        applyEvent(currentChatKey, JSON.parse(message.data) as WebEvent);
      };

      socket.onclose = () => {
        if (disposed) return;
        setConnection(currentChatKey, "disconnected");
        retryTimer = setTimeout(() => {
          retryDelay.current = Math.min(retryDelay.current * 2, MAX_DELAY);
          connect();
        }, retryDelay.current);
      };

      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();

    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, [applyEvent, chatKey, liveSessionId, setConnection]);
}
