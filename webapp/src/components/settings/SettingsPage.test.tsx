import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { SettingsPage } from "./SettingsPage";
import { renderWithProviders } from "../../test/render";
import {
  ApiError,
  fetchConfigBootstrap,
  setActiveModelProfile,
} from "../../api";
import type { ConfigBootstrapPayload } from "../../types";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return {
    ...actual,
    fetchConfigBootstrap: vi.fn(),
    createProvider: vi.fn(),
    updateProvider: vi.fn(),
    deleteProvider: vi.fn(),
    createModelProfile: vi.fn(),
    updateModelProfile: vi.fn(),
    deleteModelProfile: vi.fn(),
    setActiveModelProfile: vi.fn(),
  };
});

function makeConfigBootstrap(
  overrides: Partial<ConfigBootstrapPayload> = {},
): ConfigBootstrapPayload {
  return {
    config_revision: "rev-1",
    active_profile_id: "analysis",
    providers: [
      {
        id: "openai-main",
        name: "OpenAI Main",
        kind: "openai",
        responses_url: null,
        generic_api_url: null,
        secret_source: "env_var",
        secret_env_var: "OPENAI_API_KEY",
        has_secret: true,
      },
    ],
    model_profiles: [
      {
        id: "analysis",
        name: "Analysis",
        provider_id: "openai-main",
        provider: { id: "openai-main", name: "OpenAI Main", kind: "openai" },
        model: "gpt-5.4",
        sub_agent_model: null,
        reasoning_effort: "high",
        max_tokens: null,
        service_tier: null,
        web_search: false,
        max_tool_workers: null,
        max_retries: null,
        compact_threshold: null,
        is_active_default: true,
        resolved_runtime: {
          provider: "OpenAI",
          provider_id: "openai-main",
          profile_id: "analysis",
          model: "gpt-5.4",
          sub_agent_model: null,
          reasoning_effort: "high",
          max_tokens: 0,
          service_tier: null,
          web_search: false,
          max_tool_workers: 1,
          max_retries: 1,
          compact_threshold: 1,
          responses_url: "https://api.openai.com/v1/responses",
          generic_api_url: "https://api.openai.com/v1/chat/completions",
          supports_image_inputs: true,
        },
      },
      {
        id: "qa",
        name: "QA",
        provider_id: "openai-main",
        provider: { id: "openai-main", name: "OpenAI Main", kind: "openai" },
        model: "gpt-5.4-mini",
        sub_agent_model: null,
        reasoning_effort: "medium",
        max_tokens: null,
        service_tier: null,
        web_search: false,
        max_tool_workers: null,
        max_retries: null,
        compact_threshold: null,
        is_active_default: false,
        resolved_runtime: {
          provider: "OpenAI",
          provider_id: "openai-main",
          profile_id: "qa",
          model: "gpt-5.4-mini",
          sub_agent_model: null,
          reasoning_effort: "medium",
          max_tokens: 0,
          service_tier: null,
          web_search: false,
          max_tool_workers: 1,
          max_retries: 1,
          compact_threshold: 1,
          responses_url: "https://api.openai.com/v1/responses",
          generic_api_url: "https://api.openai.com/v1/chat/completions",
          supports_image_inputs: true,
        },
      },
    ],
    commands: [],
    options: {
      provider_kinds: ["openai"],
      reasoning_efforts: ["high", "medium"],
      openai_service_tiers: [],
      provider_metadata: {
        openai: {
          default_model: "gpt-5.4",
          default_sub_agent_model: null,
          default_responses_url: null,
          default_generic_api_url: null,
          supports_responses_url: true,
          supports_generic_api_url: false,
          supports_service_tier: true,
          supports_native_web_search: true,
          supports_image_inputs: true,
        },
      },
    },
    ...overrides,
  };
}

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.mocked(fetchConfigBootstrap).mockResolvedValue(makeConfigBootstrap());
    vi.mocked(setActiveModelProfile).mockResolvedValue({
      active_profile_id: "qa",
      config_revision: "rev-2",
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the onboarding and empty-provider states when config is blank", async () => {
    vi.mocked(fetchConfigBootstrap).mockResolvedValue(
      makeConfigBootstrap({
        providers: [],
        model_profiles: [],
        active_profile_id: null,
      }),
    );

    renderWithProviders(<SettingsPage />);

    expect(await screen.findByText(/First-time setup:/)).toBeInTheDocument();
    expect(screen.getByText("No providers configured")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Add Profile" })).toBeDisabled();
  });

  it("updates the active default profile through the API", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SettingsPage />);

    await user.selectOptions(await screen.findByRole("combobox"), "qa");

    await waitFor(() =>
      expect(setActiveModelProfile).toHaveBeenCalledWith("qa", "rev-1"),
    );
  });

  it("shows the stale-config banner when the active profile update conflicts", async () => {
    const user = userEvent.setup();
    vi.mocked(setActiveModelProfile).mockRejectedValue(
      new ApiError("Config has changed on disk.", 409),
    );

    renderWithProviders(<SettingsPage />);

    await user.selectOptions(await screen.findByRole("combobox"), "qa");

    expect(
      await screen.findByText(
        "Settings were changed while you were editing. Please review and resubmit.",
      ),
    ).toBeInTheDocument();
  });

  it("renders a settings load error when bootstrap fails", async () => {
    vi.mocked(fetchConfigBootstrap).mockRejectedValue(new Error("boom"));

    renderWithProviders(<SettingsPage />);

    expect(await screen.findByText(/Failed to load settings:/)).toBeInTheDocument();
    expect(screen.getByText(/boom/)).toBeInTheDocument();
  });
});
