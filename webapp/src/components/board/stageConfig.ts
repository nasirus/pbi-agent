import type { BoardStage, CommandView, ModelProfileView } from "../../types";

export type EditableBoardStage = {
  id: string;
  name: string;
  profile_id: string;
  command_id: string;
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
  commands: CommandView[],
): EditableBoardStage[] {
  const allowedProfileIds = new Set(profiles.map((profile) => profile.id));
  const allowedCommandIds = new Set(commands.map((command) => command.id));
  return stages.map((stage) => ({
    ...stage,
    profile_id: sanitizeReference(stage.profile_id, allowedProfileIds),
    command_id: sanitizeReference(stage.command_id, allowedCommandIds),
  }));
}

export function toEditableBoardStages(stages: BoardStage[]): EditableBoardStage[] {
  return stages.map((stage) => ({
    id: stage.id,
    name: stage.name,
    profile_id: stage.profile_id ?? "",
    command_id: stage.command_id ?? "",
    auto_start: stage.auto_start,
  }));
}
