import type { SessionRecord } from "../../types";
import { EmptyState } from "../shared/EmptyState";

export function SessionSidebar({
  sessions,
  isLoading,
  activeSessionId,
  workspaceRoot,
  onNewSession,
  onResumeSession,
}: {
  sessions: SessionRecord[];
  isLoading: boolean;
  activeSessionId: string | null;
  workspaceRoot: string | undefined;
  onNewSession: () => void;
  onResumeSession: (sessionId: string) => void;
}): JSX.Element {
  return (
    <aside className="sidebar">
      <div className="sidebar__header">
        <span className="sidebar__title">Sessions</span>
        <button type="button" className="btn btn--primary btn--sm" onClick={onNewSession}>
          + New
        </button>
      </div>

      {workspaceRoot ? (
        <div className="sidebar__workspace">
          <span className="sidebar__workspace-path" title={workspaceRoot}>
            {workspaceRoot}
          </span>
        </div>
      ) : null}

      <div className="sidebar__list">
        {isLoading ? (
          <>
            <div className="skeleton skeleton--card" />
            <div className="skeleton skeleton--card" />
            <div className="skeleton skeleton--card" />
          </>
        ) : sessions.length === 0 ? (
          <EmptyState
            title="No sessions"
            description="Start a new session to begin"
          />
        ) : (
          sessions.map((session) => (
            <button
              key={session.session_id}
              type="button"
              className={`session-card ${activeSessionId === session.session_id ? "session-card--active" : ""}`}
              onClick={() => onResumeSession(session.session_id)}
            >
              <span className="session-card__title">
                {session.title || "Untitled session"}
              </span>
              <div className="session-card__meta">
                <span>{session.updated_at.replace("T", " ").slice(0, 16)}</span>
                <span className="session-card__model">{session.model}</span>
              </div>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}
