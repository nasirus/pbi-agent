import { useEffect, useState, type FormEvent } from "react";
import type { BoardStage, ModeView, ModelProfileView } from "../../types";

type EditableBoardStage = {
  id: string;
  name: string;
  profile_id: string;
  mode_id: string;
  auto_start: boolean;
};

function initStages(stages: BoardStage[]): EditableBoardStage[] {
  return stages.map((stage) => ({
    id: stage.id,
    name: stage.name,
    profile_id: stage.profile_id ?? "",
    mode_id: stage.mode_id ?? "",
    auto_start: stage.auto_start,
  }));
}

export function BoardStageEditorModal({
  stages,
  profiles,
  modes,
  isSaving,
  onSave,
  onClose,
}: {
  stages: BoardStage[];
  profiles: ModelProfileView[];
  modes: ModeView[];
  isSaving: boolean;
  onSave: (stages: EditableBoardStage[]) => Promise<void>;
  onClose: () => void;
}) {
  const [items, setItems] = useState<EditableBoardStage[]>(() => initStages(stages));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const updateItem = (index: number, updates: Partial<EditableBoardStage>) => {
    setItems((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...updates } : item
    )));
  };

  const moveItem = (index: number, direction: -1 | 1) => {
    setItems((current) => {
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= current.length) return current;
      const next = [...current];
      const [item] = next.splice(index, 1);
      next.splice(targetIndex, 0, item);
      return next;
    });
  };

  const addStage = () => {
    setItems((current) => [
      ...current,
      {
        id: "",
        name: "",
        profile_id: "",
        mode_id: "",
        auto_start: false,
      },
    ]);
  };

  const removeStage = (index: number) => {
    setItems((current) => current.filter((_, itemIndex) => itemIndex !== index));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (items.length === 0) {
      setError("Board must contain at least one stage.");
      return;
    }
    try {
      await onSave(items);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card modal-card--board-editor" onClick={(event) => event.stopPropagation()}>
        <div className="modal-card__header">
          <h2 className="modal-card__title">Board Stages</h2>
          <button type="button" className="modal-card__close" onClick={onClose} disabled={isSaving}>
            &times;
          </button>
        </div>

        <form
          className="task-form"
          onSubmit={(event) => {
            void handleSubmit(event);
          }}
        >
          <div className="board-stage-editor">
            {items.map((item, index) => (
              <div key={`${item.id || "new"}-${index}`} className="board-stage-editor__row">
                <div className="board-stage-editor__ordering">
                  <button type="button" className="btn btn--ghost btn--sm" onClick={() => moveItem(index, -1)} disabled={index === 0 || isSaving}>
                    ↑
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => moveItem(index, 1)}
                    disabled={index === items.length - 1 || isSaving}
                  >
                    ↓
                  </button>
                </div>

                <div className="board-stage-editor__fields">
                  <div className="task-form__field">
                    <label className="task-form__label">Name</label>
                    <input
                      className="task-form__input"
                      value={item.name}
                      onChange={(event) => updateItem(index, { name: event.target.value })}
                      required
                    />
                  </div>

                  <div className="task-form__row">
                    <div className="task-form__field">
                      <label className="task-form__label">Default Profile</label>
                      <select
                        className="task-form__select"
                        value={item.profile_id}
                        onChange={(event) => updateItem(index, { profile_id: event.target.value })}
                      >
                        <option value="">No default profile</option>
                        {profiles.map((profile) => (
                          <option key={profile.id} value={profile.id}>
                            {profile.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="task-form__field">
                      <label className="task-form__label">Default Mode</label>
                      <select
                        className="task-form__select"
                        value={item.mode_id}
                        onChange={(event) => updateItem(index, { mode_id: event.target.value })}
                      >
                        <option value="">No default mode</option>
                        {modes.map((mode) => (
                          <option key={mode.id} value={mode.id}>
                            {mode.name} ({mode.slash_alias})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <label className="board-stage-editor__toggle">
                    <input
                      type="checkbox"
                      checked={item.auto_start}
                      onChange={(event) => updateItem(index, { auto_start: event.target.checked })}
                    />
                    Auto-start when a task enters this stage
                  </label>
                </div>

                <button type="button" className="btn btn--ghost-danger btn--sm" onClick={() => removeStage(index)} disabled={isSaving || items.length === 1}>
                  Remove
                </button>
              </div>
            ))}
          </div>

          {error ? <div className="settings-error-banner">{error}</div> : null}

          <div className="board-stage-editor__actions">
            <button type="button" className="btn btn--ghost" onClick={addStage} disabled={isSaving}>
              + Add Stage
            </button>
            <button type="submit" className="task-form__submit" disabled={isSaving}>
              {isSaving ? "Saving..." : "Save Board"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
