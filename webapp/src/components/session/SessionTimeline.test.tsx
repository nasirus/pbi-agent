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
});