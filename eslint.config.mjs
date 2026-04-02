import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import path from "node:path";
import { fileURLToPath } from "node:url";
import tseslint from "typescript-eslint";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const typeCheckedParserOptions = {
  projectService: true,
  tsconfigRootDir: rootDir,
};

export default tseslint.config(
  {
    ignores: [
      "node_modules/**",
      "src/pbi_agent/web/static/app/**",
      "docs/.vitepress/dist/**",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  {
    files: ["webapp/src/**/*.{ts,tsx}"],
    languageOptions: {
      globals: globals.browser,
      parserOptions: typeCheckedParserOptions,
    },
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
    },
  },
  {
    files: ["webapp/vite.config.ts"],
    languageOptions: {
      globals: globals.node,
      parserOptions: typeCheckedParserOptions,
    },
  },
);
