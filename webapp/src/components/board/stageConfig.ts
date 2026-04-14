import type { BoardStage, ModeView, ModelProfileView } from "../../types";

export type EditableBoardStage = {
  id: string;
  name: string;
  profile_id: string;
  mode_id: string;
  auto_start: boolean;
};

function sanitizeReference(value: string | null | undefined, allowedIds: Set<string>): string {
  if (!value) {
    return "";
  }
  return allowedIds.has(value) ? value : "";
}

export function sanitizeEditableBoardStages(
  stages: EditableBoardStage[],
  profiles: ModelProfileView[],
  modes: ModeView[],
): EditableBoardStage[] {
  const allowedProfileIds = new Set(profiles.map((profile) => profile.id));
  const allowedModeIds = new Set(modes.map((mode) => mode.id));
  return stages.map((stage) => ({
    ...stage,
    profile_id: sanitizeReference(stage.profile_id, allowedProfileIds),
    mode_id: sanitizeReference(stage.mode_id, allowedModeIds),
  }));
}

export function toEditableBoardStages(stages: BoardStage[]): EditableBoardStage[] {
  return stages.map((stage) => ({
    id: stage.id,
    name: stage.name,
    profile_id: stage.profile_id ?? "",
    mode_id: stage.mode_id ?? "",
    auto_start: stage.auto_start,
  }));
}
