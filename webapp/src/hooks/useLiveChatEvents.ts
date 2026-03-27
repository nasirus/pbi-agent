import { useEffect } from "react";
import { websocketUrl } from "../api";
import { useChatStore } from "../store";
import type { WebEvent } from "../types";

export function useLiveChatEvents(liveSessionId: string | null): void {
  const applyEvent = useChatStore((state) => state.applyEvent);
  const setConnection = useChatStore((state) => state.setConnection);

  useEffect(() => {
    if (!liveSessionId) {
      setConnection("disconnected");
      return;
    }
    setConnection("connecting");
    const socket = new WebSocket(websocketUrl(`/api/events/${liveSessionId}`));
    socket.onopen = () => setConnection("connected");
    socket.onmessage = (message) => {
      applyEvent(JSON.parse(message.data) as WebEvent);
    };
    socket.onerror = () => setConnection("disconnected");
    socket.onclose = () => setConnection("disconnected");
    return () => socket.close();
  }, [applyEvent, liveSessionId, setConnection]);
}
