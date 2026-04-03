import { useEffect, useState, type FormEvent } from "react";
import type { ConfigOptions, ProviderView } from "../../types";

type SecretMode = "none" | "env_var" | "plaintext";

interface FormState {
  name: string;
  id: string;
  kind: string;
  secretMode: SecretMode;
  api_key: string;
  api_key_env: string;
  responses_url: string;
  generic_api_url: string;
}

function initForm(provider?: ProviderView, kinds?: string[]): FormState {
  if (provider) {
    return {
      name: provider.name,
      id: provider.id,
      kind: provider.kind,
      secretMode:
        provider.secret_source === "env_var"
          ? "env_var"
          : provider.secret_source === "plaintext"
            ? "plaintext"
            : "none",
      api_key: "",
      api_key_env: provider.secret_env_var ?? "",
      responses_url: provider.responses_url ?? "",
      generic_api_url: provider.generic_api_url ?? "",
    };
  }
  return {
    name: "",
    id: "",
    kind: kinds?.[0] ?? "openai",
    secretMode: "env_var",
    api_key: "",
    api_key_env: "",
    responses_url: "",
    generic_api_url: "",
  };
}

export type ProviderPayload = {
  id?: string | null;
  name: string;
  kind: string;
  api_key?: string | null;
  api_key_env?: string | null;
  responses_url?: string | null;
  generic_api_url?: string | null;
};

interface Props {
  provider?: ProviderView;
  options: ConfigOptions;
  onSave: (payload: ProviderPayload) => Promise<void>;
  onClose: () => void;
}

export function ProviderModal({ provider, options, onSave, onClose }: Props) {
  const isEdit = !!provider;
  const [form, setForm] = useState<FormState>(() =>
    initForm(provider, options.provider_kinds),
  );
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  function set(updates: Partial<FormState>) {
    setForm((prev) => ({ ...prev, ...updates }));
  }

  const kindMeta = options.provider_metadata[form.kind];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setIsPending(true);
    setError(null);

    const payload: ProviderPayload = {
      name: form.name.trim(),
      kind: form.kind,
    };

    if (!isEdit && form.id.trim()) {
      payload.id = form.id.trim();
    }

    if (form.secretMode === "env_var") {
      payload.api_key_env = form.api_key_env.trim() || null;
      payload.api_key = null;
    } else if (form.secretMode === "plaintext") {
      const trimmedKey = form.api_key.trim();
      if (trimmedKey) {
        payload.api_key = trimmedKey;
      } else if (!isEdit) {
        // Create with no key supplied → explicit null
        payload.api_key = null;
      }
      // Edit with blank field → omit api_key so the existing key is preserved.
      payload.api_key_env = null;
    } else {
      payload.api_key = null;
      payload.api_key_env = null;
    }

    if (kindMeta?.supports_responses_url) {
      payload.responses_url = form.responses_url.trim() || null;
      payload.generic_api_url = null;
    } else if (kindMeta?.supports_generic_api_url) {
      payload.generic_api_url = form.generic_api_url.trim() || null;
      payload.responses_url = null;
    } else {
      payload.responses_url = null;
      payload.generic_api_url = null;
    }

    try {
      await onSave(payload);
    } catch (err) {
      setError((err as Error).message);
      setIsPending(false);
    }
  }

  const secretModes: { value: SecretMode; label: string }[] = [
    { value: "env_var", label: "Env var" },
    { value: "plaintext", label: "API key" },
    { value: "none", label: "None" },
  ];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-card__header">
          <h2 className="modal-card__title">
            {isEdit ? "Edit Provider" : "Add Provider"}
          </h2>
          <button
            type="button"
            className="modal-card__close"
            onClick={onClose}
            disabled={isPending}
          >
            &times;
          </button>
        </div>

        <form
          className="task-form"
          onSubmit={(event) => {
            void handleSubmit(event);
          }}
        >
          <div className="task-form__field">
            <label className="task-form__label">Name</label>
            <input
              name="provider-name"
              className="task-form__input"
              value={form.name}
              onChange={(e) => set({ name: e.target.value })}
              required
              autoFocus
              placeholder="e.g. My OpenAI"
            />
          </div>

          {!isEdit && (
            <div className="task-form__field">
              <label className="task-form__label">ID (optional)</label>
              <input
                name="provider-id"
                className="task-form__input"
                value={form.id}
                onChange={(e) => set({ id: e.target.value })}
                placeholder="Auto-generated from name"
              />
              <span className="task-form__hint">
                Leave blank to auto-generate from the name.
              </span>
            </div>
          )}

          <div className="task-form__field">
            <label className="task-form__label">Kind</label>
            <select
              name="provider-kind"
              className="task-form__select"
              value={form.kind}
              onChange={(e) => set({ kind: e.target.value })}
            >
              {options.provider_kinds.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </div>

          <div className="task-form__field">
            <label className="task-form__label">Authentication</label>
            <div className="secret-mode-tabs">
              {secretModes.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  className={`secret-mode-tab${form.secretMode === value ? " active" : ""}`}
                  onClick={() => set({ secretMode: value })}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {form.secretMode === "env_var" && (
            <div className="task-form__field">
              <label className="task-form__label">
                Environment variable name
              </label>
              <input
                name="api-key-env"
                className="task-form__input"
                value={form.api_key_env}
                onChange={(e) => set({ api_key_env: e.target.value })}
                placeholder="e.g. OPENAI_API_KEY"
              />
            </div>
          )}

          {form.secretMode === "plaintext" && (
            <div className="task-form__field">
              <label className="task-form__label">
                API key
                {isEdit ? " (leave blank to keep current)" : ""}
              </label>
              <input
                name="api-key"
                className="task-form__input"
                type="password"
                value={form.api_key}
                onChange={(e) => set({ api_key: e.target.value })}
                placeholder={isEdit ? "Enter new key to update" : "sk-…"}
                autoComplete="new-password"
              />
            </div>
          )}

          {kindMeta?.supports_responses_url && (
            <div className="task-form__field">
              <label className="task-form__label">
                Responses URL override
              </label>
              <input
                name="responses-url"
                className="task-form__input"
                type="text"
                value={form.responses_url}
                onChange={(e) => set({ responses_url: e.target.value })}
                placeholder={
                  kindMeta.default_responses_url ??
                  "https://api.example.com/v1/responses"
                }
              />
              <span className="task-form__hint">
                Leave blank to use the provider default.
              </span>
            </div>
          )}

          {kindMeta?.supports_generic_api_url && (
            <div className="task-form__field">
              <label className="task-form__label">API base URL</label>
              <input
                name="generic-api-url"
                className="task-form__input"
                type="text"
                value={form.generic_api_url}
                onChange={(e) => set({ generic_api_url: e.target.value })}
                placeholder={
                  kindMeta.default_generic_api_url ??
                  "https://api.example.com/v1"
                }
              />
              <span className="task-form__hint">
                Leave blank to use the provider default.
              </span>
            </div>
          )}

          {error && <div className="task-form__error">{error}</div>}

          <button
            type="submit"
            className="task-form__submit"
            disabled={isPending}
          >
            {isPending
              ? "Saving…"
              : isEdit
                ? "Save Changes"
                : "Add Provider"}
          </button>
        </form>
      </div>
    </div>
  );
}
