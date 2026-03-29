import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { searchFileMentions } from "../../api";
import type { FileMentionItem } from "../../types";

export interface ComposerHandle {
  focus: () => void;
}

interface ComposerProps {
  inputEnabled: boolean;
  sessionEnded: boolean;
  liveSessionId: string | null;
  onSubmit: (text: string, imagePaths: string[]) => Promise<void>;
}

type ActiveMention = {
  start: number;
  end: number;
  query: string;
};

const EMAIL_PREFIX_PATTERN = /[a-zA-Z0-9._%+-]$/;

function parseActiveMention(text: string, cursorIndex: number): ActiveMention | null {
  if (cursorIndex < 0 || cursorIndex > text.length) {
    return null;
  }

  const beforeCursor = text.slice(0, cursorIndex);
  const atIndex = beforeCursor.lastIndexOf("@");
  if (atIndex < 0) {
    return null;
  }
  if (atIndex > 0 && EMAIL_PREFIX_PATTERN.test(text[atIndex - 1])) {
    return null;
  }

  const candidate = text.slice(atIndex + 1, cursorIndex);
  for (let index = 0; index < candidate.length; index += 1) {
    const char = candidate[index];
    const previous = index > 0 ? candidate[index - 1] : "";
    if ((char === " " || char === "\n" || char === "\t") && previous !== "\\") {
      return null;
    }
  }

  return {
    start: atIndex,
    end: cursorIndex,
    query: candidate.replaceAll("\\ ", " "),
  };
}

function escapeMentionPath(path: string): string {
  return path.replaceAll(" ", "\\ ");
}

export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer({
  inputEnabled,
  sessionEnded,
  liveSessionId,
  onSubmit,
}, ref) {
  const [input, setInput] = useState("");
  const [imagePaths, setImagePaths] = useState("");
  const [showImages, setShowImages] = useState(false);
  const [cursorIndex, setCursorIndex] = useState(0);
  const [mentionItems, setMentionItems] = useState<FileMentionItem[]>([]);
  const [mentionOpen, setMentionOpen] = useState(false);
  const [mentionLoading, setMentionLoading] = useState(false);
  const [mentionError, setMentionError] = useState<string | null>(null);
  const [mentionSelectedIndex, setMentionSelectedIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
  }));

  const autoResize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  const canSend = Boolean(liveSessionId) && inputEnabled && !sessionEnded;
  const activeMention = parseActiveMention(input, cursorIndex);
  const activeMentionQuery = activeMention?.query ?? null;

  useEffect(() => {
    if (!canSend || activeMentionQuery === null) {
      setMentionItems([]);
      setMentionOpen(false);
      setMentionLoading(false);
      setMentionError(null);
      setMentionSelectedIndex(0);
      return undefined;
    }

    setMentionOpen(true);
    setMentionLoading(true);
    setMentionError(null);
    let cancelled = false;
    const timeoutId = window.setTimeout(async () => {
      try {
        const items = await searchFileMentions(activeMentionQuery, 8);
        if (cancelled) return;
        setMentionItems(items);
        setMentionOpen(true);
        setMentionLoading(false);
        setMentionSelectedIndex(0);
      } catch {
        if (cancelled) return;
        setMentionItems([]);
        setMentionLoading(false);
        setMentionError("Unable to load files");
        setMentionOpen(true);
      }
    }, 120);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [activeMentionQuery, canSend]);

  const syncCursor = useCallback(() => {
    setCursorIndex(textareaRef.current?.selectionStart ?? 0);
  }, []);

  const applyMention = useCallback(
    (item: FileMentionItem) => {
      const element = textareaRef.current;
      const currentText = element?.value ?? input;
      const currentCursor = element?.selectionStart ?? cursorIndex;
      const currentMention = parseActiveMention(currentText, currentCursor);
      if (!currentMention) return;

      const escapedPath = escapeMentionPath(item.path);
      const nextInput =
        currentText.slice(0, currentMention.start) +
        `@${escapedPath} ` +
        currentText.slice(currentMention.end);
      const nextCursor = currentMention.start + escapedPath.length + 2;

      setInput(nextInput);
      setCursorIndex(nextCursor);
      setMentionItems([]);
      setMentionOpen(false);
      setMentionLoading(false);
      setMentionError(null);
      setMentionSelectedIndex(0);

      window.requestAnimationFrame(() => {
        const nextElement = textareaRef.current;
        if (!nextElement) return;
        nextElement.focus();
        nextElement.selectionStart = nextCursor;
        nextElement.selectionEnd = nextCursor;
        autoResize();
      });
    },
    [autoResize, cursorIndex, input],
  );

  const handleSubmit = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed && !imagePaths.trim()) return;
    await onSubmit(
      trimmed,
      imagePaths
        .split("\n")
        .map((value) => value.trim())
        .filter(Boolean),
    );
    setInput("");
    setImagePaths("");
    setCursorIndex(0);
    setMentionItems([]);
    setMentionOpen(false);
    setMentionLoading(false);
    setMentionError(null);
    setMentionSelectedIndex(0);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (mentionOpen && mentionItems.length > 0) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setMentionSelectedIndex((prev) => (prev + 1) % mentionItems.length);
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setMentionSelectedIndex(
          (prev) => (prev - 1 + mentionItems.length) % mentionItems.length,
        );
        return;
      }
      if (event.key === "Tab" || event.key === "Enter") {
        event.preventDefault();
        applyMention(mentionItems[mentionSelectedIndex] ?? mentionItems[0]);
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        setMentionOpen(false);
        setMentionLoading(false);
        return;
      }
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  const statusText = sessionEnded
    ? "Session ended"
    : inputEnabled
      ? "Ready"
      : "Waiting for agent...";

  const statusClass = sessionEnded
    ? "composer__status composer__status--ended"
    : inputEnabled
      ? "composer__status composer__status--ready"
      : "composer__status";

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <div className="composer__input-row">
        <div className="composer__textarea-wrap">
          <textarea
            ref={textareaRef}
            className="composer__textarea"
            value={input}
            onChange={(event) => {
              setInput(event.target.value);
              setCursorIndex(event.target.selectionStart ?? event.target.value.length);
              autoResize();
            }}
            onClick={syncCursor}
            onKeyDown={handleKeyDown}
            onKeyUp={syncCursor}
            onSelect={syncCursor}
            placeholder={sessionEnded ? "Start a new session to continue..." : "Send a message..."}
            rows={1}
            disabled={!canSend}
          />
        </div>
        <button
          type="submit"
          className="composer__send"
          disabled={!canSend}
          title="Send (Enter)"
        >
          &#8593;
        </button>
      </div>

      {mentionOpen ? (
        <div className="composer__mentions" role="listbox" aria-label="Workspace file suggestions">
          {mentionLoading ? (
            <div className="composer__mention-empty">Searching files...</div>
          ) : mentionError ? (
            <div className="composer__mention-empty">{mentionError}</div>
          ) : mentionItems.length === 0 ? (
            <div className="composer__mention-empty">No matching files</div>
          ) : (
            mentionItems.map((item, index) => (
              <button
                key={item.path}
                type="button"
                className={`composer__mention-item ${index === mentionSelectedIndex ? "composer__mention-item--active" : ""}`}
                onMouseDown={(event) => {
                  event.preventDefault();
                  applyMention(item);
                }}
              >
                <span className="composer__mention-path">@{item.path}</span>
                <span className={`composer__mention-kind composer__mention-kind--${item.kind}`}>
                  {item.kind}
                </span>
              </button>
            ))
          )}
        </div>
      ) : null}

      <div className="composer__footer">
        <span className={statusClass}>{statusText}</span>
        <button
          type="button"
          className="composer__attach-toggle"
          onClick={() => setShowImages((prev) => !prev)}
        >
          {showImages ? "Hide images" : "+ Images"}
        </button>
      </div>

      {showImages ? (
        <div className="composer__image-input">
          <textarea
            className="composer__image-textarea"
            value={imagePaths}
            onChange={(event) => setImagePaths(event.target.value)}
            placeholder="Image paths, one per line"
            rows={2}
            disabled={!canSend}
          />
        </div>
      ) : null}
    </form>
  );
});
