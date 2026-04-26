import { screen } from "@testing-library/react";
import { StageColumn } from "./StageColumn";
import { renderWithProviders } from "../../test/render";
import type { BoardStage } from "../../types";

vi.mock("@dnd-kit/core", () => ({
  useDroppable: () => ({
    isOver: false,
    setNodeRef: vi.fn(),
  }),
}));

vi.mock("@dnd-kit/sortable", () => ({
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  }),
}));

vi.mock("@dnd-kit/utilities", () => ({
  CSS: {
    Transform: {
      toString: () => undefined,
    },
  },
}));

function makeStage(overrides: Partial<BoardStage> = {}): BoardStage {
  return {
    id: "review",
    name: "Review",
    position: 1,
    profile_id: "very-long-profile-name-that-should-wrap-not-overlap",
    command_id: "very-long-command-name-that-should-wrap-not-overlap-the-count-badge",
    auto_start: true,
    ...overrides,
  };
}

describe("StageColumn", () => {
  it("keeps long metadata badges in a capped wrapping header area", () => {
    const { container } = renderWithProviders(
      <StageColumn
        stage={makeStage()}
        tasks={[]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onRun={vi.fn()}
      />,
    );

    expect(
      screen.getByText("command:very-long-command-name-that-should-wrap-not-overlap-the-count-badge"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("profile:very-long-profile-name-that-should-wrap-not-overlap"),
    ).toBeInTheDocument();

    const meta = container.querySelector(".board-column__meta");
    expect(meta).toBeInTheDocument();
    expect(meta).toHaveClass("board-column__meta");
  });
});