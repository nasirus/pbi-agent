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
import { searchFileMentions, searchSlashCommands } from "../../api";
import type { FileMentionItem, SlashCommandItem } from "../../types";

export interface ComposerHandle {
  focus: () => void;
}

interface ComposerProps {
  inputEnabled: boolean;
  sessionEnded: boolean;
  liveSessionId: string | null;
  waitMessage: string | null;
  onSubmit: (text: string, imagePaths: string[]) => Promise<void>;
}

type ActiveCompletionRange = {
  start: number;
  end: number;
  query: string;
};

type CompletionMode = "mention" | "slash";

type CompletionItem =
  | {
      kind: "mention";
      key: string;
      mention: FileMentionItem;
    }
  | {
      kind: "slash";
      key: string;
      command: SlashCommandItem;
    };

const EMAIL_PREFIX_PATTERN = /[a-zA-Z0-9._%+-]$/;

function parseActiveMention(
  text: string,
  cursorIndex: number,
): ActiveCompletionRange | null {
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

function parseActiveSlashCommand(
  text: string,
  cursorIndex: number,
): ActiveCompletionRange | null {
  if (cursorIndex <= 0 || cursorIndex > text.length || !text.startsWith("/")) {
    return null;
  }

  const firstWhitespaceIndex = text.search(/\s/);
  const commandEnd = firstWhitespaceIndex >= 0 ? firstWhitespaceIndex : text.length;
  if (cursorIndex > commandEnd) {
    return null;
  }

  return {
    start: 0,
    end: cursorIndex,
    query: text.slice(1, cursorIndex),
  };
}

function escapeMentionPath(path: string): string {
  return path.replaceAll(" ", "\\ ");
}

function replaceTextRange(
  text: string,
  start: number,
  end: number,
  replacement: string,
): { nextInput: string; nextCursor: number } {
  const safeStart = Math.max(0, Math.min(start, text.length));
  const safeEnd = Math.max(safeStart, Math.min(end, text.length));
  const prefix = text.slice(0, safeStart);
  const suffix = text.slice(safeEnd);
  const insertion = suffix.startsWith(" ") ? replacement : `${replacement} `;
  return {
    nextInput: `${prefix}${insertion}${suffix}`,
    nextCursor: safeStart + insertion.length,
  };
}

export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer({
  inputEnabled,
  sessionEnded,
  liveSessionId,
  waitMessage,
  onSubmit,
}, ref) {
  const [input, setInput] = useState("");
  const [imagePaths, setImagePaths] = useState("");
  const [showImages, setShowImages] = useState(false);
  const [cursorIndex, setCursorIndex] = useState(0);
  const [completionMode, setCompletionMode] = useState<CompletionMode | null>(null);
  const [completionItems, setCompletionItems] = useState<CompletionItem[]>([]);
  const [completionOpen, setCompletionOpen] = useState(false);
  const [completionLoading, setCompletionLoading] = useState(false);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [completionSelectedIndex, setCompletionSelectedIndex] = useState(0);
  const completionRequestIdRef = useRef(0);
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
  const activeSlashCommand = parseActiveSlashCommand(input, cursorIndex);
  const activeMention = activeSlashCommand
    ? null
    : parseActiveMention(input, cursorIndex);
  const activeCompletionMode = activeSlashCommand
    ? "slash"
    : activeMention
      ? "mention"
      : null;
  const activeCompletionQuery = activeSlashCommand?.query ?? activeMention?.query ?? null;

  const closeCompletions = useCallback(() => {
    setCompletionMode(null);
    setCompletionItems([]);
    setCompletionOpen(false);
    setCompletionLoading(false);
    setCompletionError(null);
    setCompletionSelectedIndex(0);
  }, []);

  const syncCursor = useCallback(() => {
    setCursorIndex(textareaRef.current?.selectionStart ?? 0);
  }, []);

  const applyInputState = useCallback(
    (nextInput: string, nextCursor: number) => {
      setInput(nextInput);
      setCursorIndex(nextCursor);
      closeCompletions();

      window.requestAnimationFrame(() => {
        const nextElement = textareaRef.current;
        if (!nextElement) return;
        nextElement.focus();
        nextElement.selectionStart = nextCursor;
        nextElement.selectionEnd = nextCursor;
        autoResize();
      });
    },
    [autoResize, closeCompletions],
  );

  const buildMentionReplacement = useCallback(
    (
      item: FileMentionItem,
      currentText: string,
      currentCursor: number,
    ): { nextInput: string; nextCursor: number } | null => {
      const currentMention = parseActiveMention(currentText, currentCursor);
      if (!currentMention) {
        return null;
      }

      const escapedPath = escapeMentionPath(item.path);
      return replaceTextRange(
        currentText,
        currentMention.start,
        currentMention.end,
        `@${escapedPath}`,
      );
    },
    [],
  );

  const buildSlashReplacement = useCallback(
    (
      item: SlashCommandItem,
      currentText: string,
      currentCursor: number,
    ): { nextInput: string; nextCursor: number } | null => {
      const currentSlash = parseActiveSlashCommand(currentText, currentCursor);
      if (!currentSlash) {
        return null;
      }

      return replaceTextRange(currentText, 0, currentSlash.end, item.name);
    },
    [],
  );

  const applyCompletion = useCallback(
    (
      item: CompletionItem,
      currentText?: string,
      currentCursor?: number,
    ): { nextInput: string; nextCursor: number } | null => {
      const textValue = currentText ?? textareaRef.current?.value ?? input;
      const cursorValue =
        currentCursor ?? textareaRef.current?.selectionStart ?? cursorIndex;
      const nextState =
        item.kind === "mention"
          ? buildMentionReplacement(item.mention, textValue, cursorValue)
          : buildSlashReplacement(item.command, textValue, cursorValue);
      if (!nextState) {
        return null;
      }

      applyInputState(nextState.nextInput, nextState.nextCursor);
      return nextState;
    },
    [applyInputState, buildMentionReplacement, buildSlashReplacement, cursorIndex, input],
  );

  const submitValue = useCallback(
    async (textValue: string, imageValue: string) => {
      const trimmed = textValue.trim();
      if (!trimmed && !imageValue.trim()) return;
      await onSubmit(
        trimmed,
        imageValue
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
      );
      setInput("");
      setImagePaths("");
      setCursorIndex(0);
      closeCompletions();
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    },
    [closeCompletions, onSubmit],
  );

  useEffect(() => {
    if (!canSend || activeCompletionMode === null || activeCompletionQuery === null) {
      completionRequestIdRef.current += 1;
      closeCompletions();
      return undefined;
    }

    setCompletionOpen(true);
    setCompletionMode(activeCompletionMode);
    setCompletionError(null);
    setCompletionLoading(true);
    if (completionMode !== activeCompletionMode) {
      setCompletionItems([]);
      setCompletionSelectedIndex(0);
    }

    const requestId = completionRequestIdRef.current + 1;
    completionRequestIdRef.current = requestId;
    const timeoutId = window.setTimeout(async () => {
      try {
        const items =
          activeCompletionMode === "slash"
            ? (await searchSlashCommands(activeCompletionQuery, 8)).map(
                (command): CompletionItem => ({
                  kind: "slash",
                  key: command.name,
                  command,
                }),
              )
            : (await searchFileMentions(activeCompletionQuery, 8)).map(
                (mention): CompletionItem => ({
                  kind: "mention",
                  key: mention.path,
                  mention,
                }),
              );
        if (completionRequestIdRef.current !== requestId) return;
        setCompletionItems(items);
        setCompletionLoading(false);
        setCompletionSelectedIndex((previousIndex) =>
          items.length === 0 ? 0 : Math.min(previousIndex, items.length - 1),
        );
      } catch {
        if (completionRequestIdRef.current !== requestId) return;
        setCompletionLoading(false);
        setCompletionError(
          activeCompletionMode === "slash"
            ? "Unable to load commands"
            : "Unable to load files",
        );
      }
    }, activeCompletionMode === "slash" ? 60 : 120);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [
    activeCompletionMode,
    activeCompletionQuery,
    canSend,
    closeCompletions,
    completionMode,
  ]);

  const handleSubmit = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    await submitValue(input, imagePaths);
  };

  const handleSlashEnter = useCallback(async () => {
    const currentText = textareaRef.current?.value ?? input;
    const currentCursor = textareaRef.current?.selectionStart ?? cursorIndex;
    const selectedCompletion =
      completionMode === "slash"
        ? (completionItems[completionSelectedIndex] ?? completionItems[0])
        : undefined;

    if (selectedCompletion?.kind === "slash") {
      const nextState = buildSlashReplacement(
        selectedCompletion.command,
        currentText,
        currentCursor,
      );
      if (nextState) {
        await submitValue(nextState.nextInput, "");
        return;
      }
    }

    if (activeSlashCommand) {
      try {
        const commands = await searchSlashCommands(activeSlashCommand.query, 8);
        const firstMatch = commands[0];
        if (firstMatch) {
          const nextState = buildSlashReplacement(
            firstMatch,
            currentText,
            currentCursor,
          );
          if (nextState) {
            await submitValue(nextState.nextInput, "");
            return;
          }
        }
      } catch {
        // Fall back to submitting the current slash input unchanged.
      }
    }

    await submitValue(currentText, "");
  }, [
    activeSlashCommand,
    buildSlashReplacement,
    completionItems,
    completionMode,
    completionSelectedIndex,
    cursorIndex,
    input,
    submitValue,
  ]);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (completionOpen) {
      const hasCompletionItems = completionItems.length > 0;
      if (hasCompletionItems && event.key === "ArrowDown") {
        event.preventDefault();
        setCompletionSelectedIndex((prev) => (prev + 1) % completionItems.length);
        return;
      }
      if (hasCompletionItems && event.key === "ArrowUp") {
        event.preventDefault();
        setCompletionSelectedIndex(
          (prev) => (prev - 1 + completionItems.length) % completionItems.length,
        );
        return;
      }
      if (hasCompletionItems && event.key === "Tab") {
        event.preventDefault();
        void applyCompletion(
          completionItems[completionSelectedIndex] ?? completionItems[0],
        );
        return;
      }
      if (event.key === "Enter" && !event.shiftKey && completionMode === "slash") {
        event.preventDefault();
        void handleSlashEnter();
        return;
      }
      if (hasCompletionItems && event.key === "Enter") {
        event.preventDefault();
        void applyCompletion(
          completionItems[completionSelectedIndex] ?? completionItems[0],
        );
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        closeCompletions();
        return;
      }
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitValue(input, imagePaths);
    }
  };

  const statusClass = sessionEnded
    ? "composer__status composer__status--ended"
    : waitMessage
      ? "composer__status composer__status--waiting"
    : inputEnabled
      ? "composer__status composer__status--ready"
      : "composer__status";
  const showCompletionStatus = completionLoading && completionItems.length > 0;
  const showCompletionEmptyState =
    completionItems.length === 0 &&
    (completionLoading || completionError !== null || completionOpen);
  const completionEmptyText = completionLoading
    ? completionMode === "slash"
      ? "Searching commands..."
      : "Searching files..."
    : completionError ??
      (completionMode === "slash" ? "No matching commands" : "No matching files");
  const completionLabel =
    completionMode === "slash"
      ? "Slash command suggestions"
      : "Workspace file suggestions";
  const statusText = sessionEnded
    ? "Session ended"
    : waitMessage ?? (inputEnabled ? "Ready" : "Waiting for agent...");

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

      {completionOpen ? (
        <div className="composer__completions" role="listbox" aria-label={completionLabel}>
          {completionItems.length > 0 ? (
            completionItems.map((item, index) => (
              <button
                key={item.key}
                type="button"
                className={`composer__completion-item ${index === completionSelectedIndex ? "composer__completion-item--active" : ""}`}
                onMouseDown={(event) => {
                  event.preventDefault();
                  void applyCompletion(item);
                }}
              >
                <span className="composer__completion-copy">
                  <span className="composer__completion-label">
                    {item.kind === "slash" ? item.command.name : `@${item.mention.path}`}
                  </span>
                  {item.kind === "slash" ? (
                    <span className="composer__completion-description">
                      {item.command.description}
                    </span>
                  ) : null}
                </span>
                {item.kind === "mention" ? (
                  <span
                    className={`composer__completion-kind composer__completion-kind--${item.mention.kind}`}
                  >
                    {item.mention.kind}
                  </span>
                ) : null}
              </button>
            ))
          ) : showCompletionEmptyState ? (
            <div className="composer__completion-empty">{completionEmptyText}</div>
          ) : null}
          {showCompletionStatus ? (
            <div className="composer__completion-status">
              {completionMode === "slash" ? "Updating commands..." : "Updating results..."}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="composer__footer">
        <span
          className={statusClass}
          role={waitMessage ? "status" : undefined}
          aria-live={waitMessage ? "polite" : undefined}
        >
          {waitMessage ? <span className="composer__status-dot" aria-hidden="true" /> : null}
          <span className="composer__status-text">{statusText}</span>
        </span>
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
