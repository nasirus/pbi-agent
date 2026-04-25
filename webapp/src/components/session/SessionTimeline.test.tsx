import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SessionTimeline } from "./SessionTimeline";

describe("SessionTimeline", () => {
  beforeEach(() => {
    HTMLElement.prototype.scrollTo = vi.fn();
  });

  it("shows a waiting state for connected live sessions with no events yet", () => {
    render(
      <SessionTimeline
        items={[]}
        subAgents={{}}
        connection="connected"
        waitMessage={null}
        itemsVersion={0}
      />,
    );

    expect(
      screen.getByText("Session started. Waiting for updates…"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Live events will appear here as soon as the session produces output.",
      ),
    ).toBeInTheDocument();
  });

  it("preserves user-authored line breaks in message text", () => {
    const content =
      "/plan\n# Task\nadd shell command from UI\n\n## Goal\nPossibility to can run any shell command from UI using ! (e.g. !ls), use bash_tool in backend";

    render(
      <SessionTimeline
        items={[
          {
            kind: "message",
            itemId: "user-1",
            role: "user",
            content,
            markdown: false,
          },
        ]}
        subAgents={{}}
        connection="connected"
        waitMessage={null}
        itemsVersion={1}
      />,
    );

    const userText = document.querySelector(".timeline-entry__user-text");
    expect(userText).not.toBeNull();
    expect(userText).toHaveClass("timeline-entry__user-text");
    expect(userText?.textContent).toBe(content);
    expect(userText?.textContent).toContain("/plan\n# Task\nadd shell command from UI");
  });

  it("still highlights file paths inside formatted user text", () => {
    render(
      <SessionTimeline
        items={[
          {
            kind: "message",
            itemId: "user-1",
            role: "user",
            content: "Please inspect\nwebapp/src/App.tsx",
            filePaths: ["webapp/src/App.tsx"],
            markdown: false,
          },
        ]}
        subAgents={{}}
        connection="connected"
        waitMessage={null}
        itemsVersion={1}
      />,
    );

    expect(screen.getByText("webapp/src/App.tsx")).toHaveClass(
      "timeline-entry__file-tag",
    );
    expect(screen.getByText(/Please inspect/)).toHaveClass(
      "timeline-entry__user-text",
    );
  });

  it("keeps assistant markdown rendering separate from user text formatting", () => {
    render(
      <SessionTimeline
        items={[
          {
            kind: "message",
            itemId: "assistant-1",
            role: "assistant",
            content: "# Done",
            markdown: true,
          },
        ]}
        subAgents={{}}
        connection="connected"
        waitMessage={null}
        itemsVersion={1}
      />,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Done" })).toBeInTheDocument();
    expect(screen.queryByText("# Done")).not.toBeInTheDocument();
  });

  it("renders apply_patch tool results as a structured git diff", () => {
    render(
      <SessionTimeline
        items={[
          {
            kind: "tool_group",
            itemId: "tool-1",
            label: "apply_patch",
            items: [
              {
                text: "update_file TODO.md  done\ndiff:\n-[ ] Old\n+[X] New",
                classes: "tool-call-apply-patch",
                metadata: {
                  tool_name: "apply_patch",
                  path: "TODO.md",
                  operation: "update_file",
                  success: true,
                  diff: "-[ ] Old\n+[X] New",
                  call_id: "call_patch_1",
                },
              },
            ],
          },
        ]}
        subAgents={{}}
        connection="connected"
        waitMessage={null}
        itemsVersion={1}
      />,
    );

    expect(screen.getByText("TODO.md")).toBeInTheDocument();
    expect(screen.getByText("Updated")).toBeInTheDocument();
    expect(screen.getByText("[ ] Old")).toBeInTheDocument();
    expect(screen.getByText("[X] New")).toBeInTheDocument();
    expect(screen.getByText("call_patch_1")).toBeInTheDocument();
    expect(screen.queryByText(/update_file TODO.md/)).not.toBeInTheDocument();
  });
});
