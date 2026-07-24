import { defineConfig, globalIgnores } from "eslint/config";
import eslintConfigPrettier from "eslint-config-prettier";
import * as mdx from "eslint-plugin-mdx";
import importX from "eslint-plugin-import-x";
import unicorn from "eslint-plugin-unicorn";
import tseslint from "typescript-eslint";

const sourceFiles = ["**/*.{ts,tsx,mts,cts,js,jsx,mjs,cjs}"];

const eslintConfig = defineConfig([
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: {
          allowDefaultProject: ["astro.config.mjs", "eslint.config.mjs"],
          defaultProject: "tsconfig.json",
        },
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    files: ["*.mjs", "scripts/*.mts"],
    rules: tseslint.configs.disableTypeChecked.rules,
  },
  {
    files: ["**/*.{md,mdx}", "**/*.{md,mdx}/**"],
    rules: tseslint.configs.disableTypeChecked.rules,
  },
  {
    files: sourceFiles,
    rules: {
      "@typescript-eslint/ban-ts-comment": [
        "error",
        {
          "ts-ignore": false,
          "ts-expect-error": "allow-with-description",
          "ts-nocheck": false,
          "ts-check": false,
          minimumDescriptionLength: 3,
        },
      ],
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-misused-promises": "error",
      "@typescript-eslint/no-non-null-assertion": "error",
      "@typescript-eslint/no-unnecessary-type-assertion": "error",
      "@typescript-eslint/prefer-optional-chain": "error",
      "@typescript-eslint/require-await": "error",
    },
  },
  {
    plugins: { unicorn, "import-x": importX },
  },
  {
    settings: importX.flatConfigs.typescript.settings,
  },
  {
    files: sourceFiles,
    rules: {
      ...importX.flatConfigs.recommended.rules,
      ...unicorn.configs.recommended.rules,
      "import-x/no-cycle": "error",
      "import-x/order": "error",
      "unicorn/consistent-boolean-name": "off",
      "unicorn/consistent-function-scoping": "off",
      "unicorn/filename-case": [
        "error",
        {
          cases: { kebabCase: true, pascalCase: true },
          checkDirectories: false,
          multipleFileExtensions: true,
        },
      ],
      "unicorn/name-replacements": "off",
      "unicorn/no-array-callback-reference": "off",
      "unicorn/no-array-reduce": "off",
      "unicorn/no-for-each": "error",
      "unicorn/no-null": "off",
      "unicorn/no-object-as-default-parameter": "off",
      "unicorn/prevent-abbreviations": "off",
    },
  },
  {
    files: ["*.mjs", "scripts/*.mts"],
    rules: {
      "import-x/no-named-as-default": "off",
      "import-x/no-named-as-default-member": "off",
      "unicorn/no-process-exit": "off",
      "unicorn/no-top-level-side-effects": "off",
      "unicorn/prefer-module": "off",
      "unicorn/prefer-top-level-await": "off",
    },
  },
  mdx.flat,
  {
    files: ["**/*.{md,mdx}"],
    processor: mdx.createRemarkProcessor({
      lintCodeBlocks: true,
    }),
  },
  mdx.flatCodeBlocks,
  {
    files: ["**/*.{md,mdx}/**"],
    rules: {
      ...mdx.flatCodeBlocks.rules,
      "@typescript-eslint/no-floating-promises": "off",
      "@typescript-eslint/no-misused-promises": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
      "@typescript-eslint/no-unnecessary-type-assertion": "off",
      "@typescript-eslint/prefer-optional-chain": "off",
      "@typescript-eslint/require-await": "off",
      "no-var": "error",
      "prefer-const": "error",
    },
  },
  {
    files: ["*.config.ts", "playwright.config.ts", "vitest.config.ts"],
    rules: {
      "unicorn/no-top-level-side-effects": "off",
    },
  },
  {
    files: ["src/content.config.ts"],
    rules: {
      "import-x/no-unresolved": "off",
    },
  },
  globalIgnores([
    ".astro/**",
    ".cache/**",
    ".next/**",
    ".source/**",
    "coverage/**",
    "dist/**",
    "out/**",
  ]),
  eslintConfigPrettier,
]);

export default eslintConfig;
