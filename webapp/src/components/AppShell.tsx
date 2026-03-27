import { NavLink, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchBootstrap } from "../api";
import { useTaskEvents } from "../hooks/useTaskEvents";
import { ChatPage } from "./chat/ChatPage";
import { BoardPage } from "./board/BoardPage";

export function AppShell(): JSX.Element {
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
        <div className="topbar__brand">
          <strong>Agent</strong> Control Room
        </div>
        <nav className="topnav">
          <NavLink to="/" end>Chat</NavLink>
          <NavLink to="/board">Board</NavLink>
        </nav>
        <div className="runtime-meta">
          <span className="runtime-meta__pill">{bootstrap?.provider ?? "..."}</span>
          <span className="runtime-meta__pill">{bootstrap?.model ?? "..."}</span>
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
