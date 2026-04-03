import { useDroppable } from "@dnd-kit/core";
import type { BoardStage, TaskRecord } from "../../types";
import { EmptyState } from "../shared/EmptyState";
import { TaskCard } from "./TaskCard";

export function StageColumn({
  stage,
  tasks,
  onEdit,
  onDelete,
  onRun,
}: {
  stage: BoardStage;
  tasks: TaskRecord[];
  onEdit: (task: TaskRecord) => void;
  onDelete: (taskId: string) => void;
  onRun: (taskId: string) => void;
}) {
  const { isOver, setNodeRef } = useDroppable({
    id: `stage:${stage.id}`,
    data: { stage: stage.id },
  });

  return (
    <section
      ref={setNodeRef}
      className={`board-column${isOver ? " board-column--drop-over" : ""}`}
    >
      <header className="board-column__header">
        <div className="board-column__heading">
          <span className="board-column__name">{stage.name}</span>
          <div className="board-column__meta">
            {stage.auto_start ? (
              <span className="board-column__label">auto-start</span>
            ) : null}
            {stage.mode_id ? (
              <span className="board-column__label">mode:{stage.mode_id}</span>
            ) : null}
            {stage.profile_id ? (
              <span className="board-column__label">profile:{stage.profile_id}</span>
            ) : null}
          </div>
        </div>
        <span className="board-column__count">{tasks.length}</span>
      </header>
      <div className="board-column__body">
        {tasks.length === 0 ? (
          <EmptyState title="No tasks" />
        ) : (
          tasks.map((task) => (
            <TaskCard
              key={task.task_id}
              task={task}
              onEdit={() => onEdit(task)}
              onDelete={() => onDelete(task.task_id)}
              onRun={() => onRun(task.task_id)}
            />
          ))
        )}
      </div>
    </section>
  );
}
