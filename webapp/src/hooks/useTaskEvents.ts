import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { websocketUrl } from "../api";
import type { WebEvent } from "../types";

export function useTaskEvents(): void {
  const client = useQueryClient();

  useEffect(() => {
    const socket = new WebSocket(websocketUrl("/api/events/app"));
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as WebEvent;
      if (event.type === "task_updated" || event.type === "task_deleted") {
        client.invalidateQueries({ queryKey: ["tasks"] });
      }
    };
    return () => socket.close();
  }, [client]);
}
