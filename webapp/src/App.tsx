import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import {
  DndContext,
  useDraggable,
  useDroppable,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createChatSession,
  createTask,
  deleteTask,
  fetchBootstrap,
  fetchSessions,
  fetchTasks,
  requestNewChat,
  runTask,
  submitChatInput,
  updateTask,
  websocketUrl,
} from "./api";
import { useChatStore } from "./store";
import type { TaskRecord, TimelineItem, WebEvent } from "./types";

const queryClient = new QueryClient();
const BOARD_STAGES = ["backlog", "plan", "processing", "review"] as const;

type EditableTask = {
  taskId?: string;
  title: string;
  prompt: string;
  stage: "backlog" | "plan" | "review";
  projectDir: string;
  sessionId: string;
};

function useTaskEvents(): void {
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

function useLiveChatEvents(liveSessionId: string | null): void {
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

function formatStageLabel(stage: string): string {
  return stage.charAt(0).toUpperCase() + stage.slice(1);
}

function AppShell(): JSX.Element {
  useTaskEvents();
  const bootstrapQuery = useQuery({
    queryKey: ["bootstrap"],
    queryFn: fetchBootstrap,
    staleTime: 30000,
  });

  const bootstrap = bootstrapQuery.data;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">PBI Agent</div>
          <h1>Local Agent Control Room</h1>
        </div>
        <nav className="topnav">
          <NavLink to="/" end>
            Chat
          </NavLink>
          <NavLink to="/board">Board</NavLink>
        </nav>
        <div className="runtime-meta">
          <span>{bootstrap?.provider ?? "provider"}</span>
          <span>{bootstrap?.model ?? "model"}</span>
        </div>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<ChatPage workspaceRoot={bootstrap?.workspace_root} />} />
          <Route path="/board" element={<BoardPage />} />
        </Routes>
      </main>
    </div>
  );
}

function ChatPage({
  workspaceRoot,
}: {
  workspaceRoot: string | undefined;
}): JSX.Element {
  const liveSessionId = useChatStore((state) => state.liveSessionId);
  const switchLiveSession = useChatStore((state) => state.switchLiveSession);
  const clearTimeline = useChatStore((state) => state.clearTimeline);
  const connection = useChatStore((state) => state.connection);
  const inputEnabled = useChatStore((state) => state.inputEnabled);
  const waitMessage = useChatStore((state) => state.waitMessage);
  const sessionUsage = useChatStore((state) => state.sessionUsage);
  const turnUsage = useChatStore((state) => state.turnUsage);
  const sessionEnded = useChatStore((state) => state.sessionEnded);
  const fatalError = useChatStore((state) => state.fatalError);
  const items = useChatStore((state) => state.items);
  const subAgents = useChatStore((state) => state.subAgents);

  const sessionsQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: fetchSessions,
    refetchInterval: 12000,
  });

  const createSessionMutation = useMutation({
    mutationFn: createChatSession,
    onSuccess: (session) => {
      switchLiveSession(session.live_session_id);
    },
  });

  const sendInputMutation = useMutation({
    mutationFn: (payload: { text: string; image_paths: string[] }) => {
      if (!liveSessionId) {
        throw new Error("No live session available.");
      }
      return submitChatInput(liveSessionId, payload);
    },
  });

  const newChatMutation = useMutation({
    mutationFn: () => {
      if (!liveSessionId) {
        throw new Error("No live session available.");
      }
      return requestNewChat(liveSessionId);
    },
    onSuccess: () => clearTimeline(),
  });

  const startedRef = useRef(false);
  useLiveChatEvents(liveSessionId);

  useEffect(() => {
    if (startedRef.current) {
      return;
    }
    startedRef.current = true;
    createSessionMutation.mutate(
      liveSessionId ? { live_session_id: liveSessionId } : {},
    );
  }, [createSessionMutation, liveSessionId]);

  const [input, setInput] = useState("");
  const [imagePaths, setImagePaths] = useState("");

  const timeline = useMemo(() => items, [items]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed && !imagePaths.trim()) {
      return;
    }
    await sendInputMutation.mutateAsync({
      text: trimmed,
      image_paths: imagePaths
        .split("\n")
        .map((value) => value.trim())
        .filter(Boolean),
    });
    setInput("");
    setImagePaths("");
  };

  return (
    <section className="chat-layout">
      <aside className="panel sidebar">
        <div className="panel-header">
          <h2>Sessions</h2>
          <button
            type="button"
            className="ghost-button"
            onClick={() => createSessionMutation.mutate({})}
          >
            New Live Session
          </button>
        </div>
        <div className="workspace-meta">
          <span>Workspace</span>
          <strong>{workspaceRoot ?? "Loading..."}</strong>
        </div>
        <div className="session-list">
          {sessionsQuery.data?.map((session) => (
            <button
              key={session.session_id}
              type="button"
              className="session-card"
              onClick={() =>
                createSessionMutation.mutate({
                  resume_session_id: session.session_id,
                })
              }
            >
              <strong>{session.title || "Untitled session"}</strong>
              <span>{session.updated_at.replace("T", " ").slice(0, 16)}</span>
              <span>{session.model}</span>
            </button>
          ))}
        </div>
      </aside>

      <div className="panel chat-panel">
        <div className="panel-header">
          <div>
            <h2>Chat</h2>
            <p className="muted">
              {connection === "connected"
                ? "Live websocket connected"
                : connection === "connecting"
                  ? "Connecting..."
                  : "Disconnected"}
            </p>
          </div>
          <button
            type="button"
            className="ghost-button"
            onClick={() => newChatMutation.mutate()}
            disabled={!liveSessionId || newChatMutation.isPending}
          >
            Reset Current Chat
          </button>
        </div>

        {waitMessage ? <div className="status-banner">{waitMessage}</div> : null}
        {fatalError ? <div className="error-banner">{fatalError}</div> : null}

        <div className="timeline">
          {timeline.map((item) => (
            <TimelineEntry
              key={item.itemId}
              item={item}
              subAgentTitle={item.subAgentId ? subAgents[item.subAgentId]?.title : undefined}
              subAgentStatus={item.subAgentId ? subAgents[item.subAgentId]?.status : undefined}
            />
          ))}
        </div>

        <footer className="usage-bar">
          <div>
            <span className="muted">Session tokens</span>
            <strong>{sessionUsage?.total_tokens ?? 0}</strong>
          </div>
          <div>
            <span className="muted">Estimated cost</span>
            <strong>${(sessionUsage?.estimated_cost_usd ?? 0).toFixed(4)}</strong>
          </div>
          <div>
            <span className="muted">Last turn</span>
            <strong>
              {turnUsage
                ? `${turnUsage.usage.total_tokens} tokens / ${turnUsage.elapsedSeconds?.toFixed(1) ?? "0.0"}s`
                : "No turns yet"}
            </strong>
          </div>
        </footer>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Type a prompt for the current live chat..."
            rows={5}
            disabled={!inputEnabled || sessionEnded}
          />
          <textarea
            value={imagePaths}
            onChange={(event) => setImagePaths(event.target.value)}
            placeholder="Optional image paths, one per line"
            rows={2}
            disabled={!inputEnabled || sessionEnded}
          />
          <div className="composer-actions">
            <span className="muted">
              {sessionEnded
                ? "This live session ended. Start or resume another one."
                : inputEnabled
                  ? "Ready for input"
                  : "Waiting for the agent loop"}
            </span>
            <button
              type="submit"
              className="primary-button"
              disabled={!liveSessionId || !inputEnabled || sessionEnded}
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}

function TimelineEntry({
  item,
  subAgentTitle,
  subAgentStatus,
}: {
  item: TimelineItem;
  subAgentTitle?: string;
  subAgentStatus?: string;
}): JSX.Element {
  const subAgentMeta =
    subAgentTitle || subAgentStatus ? (
      <div className="subagent-meta">
        <span>{subAgentTitle ?? "sub_agent"}</span>
        <span>{subAgentStatus ?? "running"}</span>
      </div>
    ) : null;

  if (item.kind === "message") {
    return (
      <article className={`timeline-card message-${item.role}`}>
        {subAgentMeta}
        {item.markdown ? (
          <ReactMarkdown>{item.content}</ReactMarkdown>
        ) : (
          <p>{item.content}</p>
        )}
      </article>
    );
  }

  if (item.kind === "thinking") {
    return (
      <article className="timeline-card thinking-card">
        {subAgentMeta}
        <header>{item.title}</header>
        <ReactMarkdown>{item.content}</ReactMarkdown>
      </article>
    );
  }

  return (
    <article className="timeline-card tool-card">
      {subAgentMeta}
      <header>{item.label}</header>
      <div className="tool-items">
        {item.items.map((toolItem, index) => (
          <pre key={`${item.itemId}-${index}`}>{toolItem.text}</pre>
        ))}
      </div>
    </article>
  );
}

function BoardPage(): JSX.Element {
  const client = useQueryClient();
  const tasksQuery = useQuery({
    queryKey: ["tasks"],
    queryFn: fetchTasks,
  });
  const [editingTask, setEditingTask] = useState<EditableTask | null>(null);

  const createTaskMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => client.invalidateQueries({ queryKey: ["tasks"] }),
  });
  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: Record<string, unknown> }) =>
      updateTask(taskId, payload),
    onSuccess: () => client.invalidateQueries({ queryKey: ["tasks"] }),
  });
  const deleteTaskMutation = useMutation({
    mutationFn: deleteTask,
    onSuccess: () => client.invalidateQueries({ queryKey: ["tasks"] }),
  });
  const runTaskMutation = useMutation({
    mutationFn: runTask,
    onSuccess: () => client.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const tasks = tasksQuery.data ?? [];
  const tasksByStage = useMemo(
    () =>
      BOARD_STAGES.reduce<Record<string, TaskRecord[]>>((accumulator, stage) => {
        accumulator[stage] = tasks
          .filter((task) => task.stage === stage)
          .sort((left, right) => left.position - right.position);
        return accumulator;
      }, {}),
    [tasks],
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const taskId = String(event.active.id);
    const overStage = event.over?.data.current?.stage as TaskRecord["stage"] | undefined;
    if (!overStage || overStage === "processing") {
      return;
    }
    const task = tasks.find((entry) => entry.task_id === taskId);
    if (!task || task.stage === overStage) {
      return;
    }
    updateTaskMutation.mutate({ taskId, payload: { stage: overStage } });
  };

  const openNewTask = () =>
    setEditingTask({
      title: "",
      prompt: "",
      stage: "backlog",
      projectDir: ".",
      sessionId: "",
    });

  const openEditTask = (task: TaskRecord) =>
    setEditingTask({
      taskId: task.task_id,
      title: task.title,
      prompt: task.prompt,
      stage: task.stage === "processing" ? "review" : task.stage,
      projectDir: task.project_dir,
      sessionId: task.session_id ?? "",
    });

  const saveTask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingTask) {
      return;
    }
    if (editingTask.taskId) {
      await updateTaskMutation.mutateAsync({
        taskId: editingTask.taskId,
        payload: {
          title: editingTask.title,
          prompt: editingTask.prompt,
          stage: editingTask.stage,
          project_dir: editingTask.projectDir,
          session_id: editingTask.sessionId || undefined,
          clear_session_id: editingTask.sessionId.trim() === "",
        },
      });
    } else {
      await createTaskMutation.mutateAsync({
        title: editingTask.title,
        prompt: editingTask.prompt,
        stage: editingTask.stage,
        project_dir: editingTask.projectDir,
        session_id: editingTask.sessionId || undefined,
      });
    }
    setEditingTask(null);
  };

  return (
    <section className="board-layout">
      <div className="panel board-panel">
        <div className="panel-header">
          <div>
            <h2>Kanban Board</h2>
            <p className="muted">
              Background runs update live over the workspace event stream.
            </p>
          </div>
          <button type="button" className="primary-button" onClick={openNewTask}>
            Add Task
          </button>
        </div>

        <DndContext onDragEnd={handleDragEnd}>
          <div className="board-grid">
            {BOARD_STAGES.map((stage) => (
              <StageColumn
                key={stage}
                stage={stage}
                tasks={tasksByStage[stage] ?? []}
                onEdit={openEditTask}
                onDelete={(taskId) => deleteTaskMutation.mutate(taskId)}
                onRun={(taskId) => runTaskMutation.mutate(taskId)}
              />
            ))}
          </div>
        </DndContext>
      </div>

      {editingTask ? (
        <div className="modal-backdrop" onClick={() => setEditingTask(null)}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="panel-header">
              <h2>{editingTask.taskId ? "Edit Task" : "Create Task"}</h2>
              <button
                type="button"
                className="ghost-button"
                onClick={() => setEditingTask(null)}
              >
                Close
              </button>
            </div>
            <form className="task-form" onSubmit={saveTask}>
              <label>
                Title
                <input
                  value={editingTask.title}
                  onChange={(event) =>
                    setEditingTask((current) =>
                      current ? { ...current, title: event.target.value } : current,
                    )
                  }
                  required
                />
              </label>
              <label>
                Prompt
                <textarea
                  value={editingTask.prompt}
                  onChange={(event) =>
                    setEditingTask((current) =>
                      current ? { ...current, prompt: event.target.value } : current,
                    )
                  }
                  rows={7}
                  required
                />
              </label>
              <label>
                Stage
                <select
                  value={editingTask.stage}
                  onChange={(event) =>
                    setEditingTask((current) =>
                      current
                        ? {
                            ...current,
                            stage: event.target.value as EditableTask["stage"],
                          }
                        : current,
                    )
                  }
                >
                  <option value="backlog">Backlog</option>
                  <option value="plan">Plan</option>
                  <option value="review">Review</option>
                </select>
              </label>
              <label>
                Project Directory
                <input
                  value={editingTask.projectDir}
                  onChange={(event) =>
                    setEditingTask((current) =>
                      current ? { ...current, projectDir: event.target.value } : current,
                    )
                  }
                />
              </label>
              <label>
                Session ID
                <input
                  value={editingTask.sessionId}
                  onChange={(event) =>
                    setEditingTask((current) =>
                      current ? { ...current, sessionId: event.target.value } : current,
                    )
                  }
                />
              </label>
              <button type="submit" className="primary-button">
                Save Task
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function StageColumn({
  stage,
  tasks,
  onEdit,
  onDelete,
  onRun,
}: {
  stage: (typeof BOARD_STAGES)[number];
  tasks: TaskRecord[];
  onEdit: (task: TaskRecord) => void;
  onDelete: (taskId: string) => void;
  onRun: (taskId: string) => void;
}): JSX.Element {
  const { isOver, setNodeRef } = useDroppable({
    id: `stage:${stage}`,
    data: { stage },
    disabled: stage === "processing",
  });

  return (
    <section
      ref={setNodeRef}
      className={`board-column ${isOver ? "is-over" : ""} ${stage === "processing" ? "read-only" : ""}`}
    >
      <header>
        <h3>{formatStageLabel(stage)}</h3>
        <span>{tasks.length}</span>
      </header>
      <div className="column-body">
        {tasks.map((task) => (
          <TaskCard
            key={task.task_id}
            task={task}
            onEdit={() => onEdit(task)}
            onDelete={() => onDelete(task.task_id)}
            onRun={() => onRun(task.task_id)}
          />
        ))}
      </div>
    </section>
  );
}

function TaskCard({
  task,
  onEdit,
  onDelete,
  onRun,
}: {
  task: TaskRecord;
  onEdit: () => void;
  onDelete: () => void;
  onRun: () => void;
}): JSX.Element {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.task_id,
    disabled: task.stage === "processing",
    data: { taskId: task.task_id, stage: task.stage },
  });

  const style =
    transform != null
      ? {
          transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        }
      : undefined;

  return (
    <article
      ref={setNodeRef}
      className={`task-card ${isDragging ? "dragging" : ""}`}
      style={style}
      {...listeners}
      {...attributes}
    >
      <div className="task-card-top">
        <strong>{task.title}</strong>
        <span className={`status-pill status-${task.run_status}`}>{task.run_status}</span>
      </div>
      <p>{task.prompt}</p>
      <div className="task-meta">
        <span>{task.project_dir}</span>
        <span>{task.session_id ?? "no session"}</span>
      </div>
      <div className="task-summary">{task.last_result_summary || "No run output yet."}</div>
      <div className="task-actions">
        <button type="button" className="ghost-button" onClick={onEdit}>
          Edit
        </button>
        <button
          type="button"
          className="ghost-button"
          onClick={onRun}
          disabled={task.run_status === "running"}
        >
          Run
        </button>
        <button type="button" className="ghost-button danger" onClick={onDelete}>
          Delete
        </button>
      </div>
    </article>
  );
}

export default function App(): JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell />
    </QueryClientProvider>
  );
}
