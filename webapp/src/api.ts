import type {
  BootstrapPayload,
  LiveSession,
  SessionRecord,
  TaskRecord,
} from "./types";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    throw new Error(payload.detail || `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function websocketUrl(path: string): string {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.host}${path}`;
}

export async function fetchBootstrap(): Promise<BootstrapPayload> {
  return requestJson<BootstrapPayload>("/api/bootstrap");
}

export async function fetchSessions(): Promise<SessionRecord[]> {
  const result = await requestJson<{ sessions: SessionRecord[] }>("/api/sessions");
  return result.sessions;
}

export async function createChatSession(
  payload: Partial<{
    live_session_id: string;
    resume_session_id: string;
  }> = {},
): Promise<LiveSession> {
  const result = await requestJson<{ session: LiveSession }>("/api/chat/session", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return result.session;
}

export async function submitChatInput(
  liveSessionId: string,
  payload: { text: string; image_paths: string[] },
): Promise<LiveSession> {
  const result = await requestJson<{ session: LiveSession }>(
    `/api/chat/session/${liveSessionId}/input`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
  return result.session;
}

export async function requestNewChat(liveSessionId: string): Promise<LiveSession> {
  const result = await requestJson<{ session: LiveSession }>(
    `/api/chat/session/${liveSessionId}/new-chat`,
    { method: "POST" },
  );
  return result.session;
}

export async function fetchTasks(): Promise<TaskRecord[]> {
  const result = await requestJson<{ tasks: TaskRecord[] }>("/api/tasks");
  return result.tasks;
}

export async function createTask(
  payload: Partial<TaskRecord> & { title: string; prompt: string },
): Promise<TaskRecord> {
  const result = await requestJson<{ task: TaskRecord }>("/api/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return result.task;
}

export async function updateTask(
  taskId: string,
  payload: Partial<TaskRecord> & { clear_session_id?: boolean },
): Promise<TaskRecord> {
  const result = await requestJson<{ task: TaskRecord }>(`/api/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return result.task;
}

export async function deleteTask(taskId: string): Promise<void> {
  await requestJson<void>(`/api/tasks/${taskId}`, { method: "DELETE" });
}

export async function runTask(taskId: string): Promise<TaskRecord> {
  const result = await requestJson<{ task: TaskRecord }>(`/api/tasks/${taskId}/run`, {
    method: "POST",
  });
  return result.task;
}
