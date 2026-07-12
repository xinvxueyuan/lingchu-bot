import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';
import eslintConfigPrettier from 'eslint-config-prettier';
import * as mdx from 'eslint-plugin-mdx';
import tseslint from 'typescript-eslint';
import importX from 'eslint-plugin-import-x';
import unicorn from 'eslint-plugin-unicorn';

// Source files that should receive the full import / unicorn / type-checked rule set.
// Excludes .md/.mdx and their virtual code-block sub-paths (**/*.{md,mdx}/**).
const sourceFiles = ['**/*.{ts,tsx,mts,cts,js,jsx,mjs,cjs}'];

const eslintConfig = defineConfig([
  // Next.js core-web-vitals + TypeScript configs (existing)
  ...nextVitals,
  ...nextTs,

  // #89764 mitigation: pin react version to bypass eslint-plugin-react auto-detection crash on ESLint 10
  {
    settings: {
      react: { version: '19' },
    },
  },

  // typescript-eslint type-checked rules.
  // Uses projectService (TS Project Service) instead of the deprecated `project` option to
  // automatically resolve the correct tsconfig per file. recommendedTypeChecked enables rules
  // that require type information (no-floating-promises, no-misused-promises, etc.).
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: {
          // Non-tsconfig files (.mjs/.mts/.cjs) are not included in tsconfig.json (which only
          // covers **/*.ts and **/*.tsx). Allow them to fall back to the default project so
          // they lint without fatal "no project" errors. Note: *.config.ts files (vitest.config.ts,
          // playwright.config.ts, source.config.ts) ARE in tsconfig via **/*.ts, so they must NOT
          // be listed here — otherwise projectService reports a conflict. `allowDefaultProject`
          // does not allow `**` globs, so subdirectory files must be listed explicitly.
          allowDefaultProject: ['*.mjs', '*.cjs', 'scripts/*.mts'],
          defaultProject: 'tsconfig.json',
        },
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },

  // Type-checked rule overrides: enforce the project's async-safety invariants as errors.
  {
    files: ['**/*.{ts,tsx,mts,cts}'],
    rules: {
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      // require-await relaxed to warn: Next.js framework conventions require many functions to be
      // async even when they don't use await — generateStaticParams, Layout/Image components,
      // route handlers, baseOptions(), buildGraph(), getRSS() (per AGENTS.md). Test callbacks
      // are also often async-by-convention. Warnings don't block lint exit code.
      '@typescript-eslint/require-await': 'warn',
      '@typescript-eslint/no-unnecessary-type-assertion': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
    },
  },

  // Disable type-checked rules for config files (.mjs/.mts/.cjs) that are in allowDefaultProject.
  // These files have limited type information from the default project, causing false positives
  // like no-unsafe-assignment on import.meta.dirname.
  {
    files: ['*.mjs', '*.cjs', 'scripts/*.mts'],
    rules: tseslint.configs.disableTypeChecked.rules,
  },

  // Disable all type-checked rules for .md/.mdx files and their embedded code blocks.
  // These files are parsed by eslint-mdx (not @typescript-eslint/parser), so type information
  // is unavailable and type-checked rules would fatal. disableTypeChecked turns off all 61.
  {
    files: ['**/*.{md,mdx}', '**/*.{md,mdx}/**'],
    rules: tseslint.configs.disableTypeChecked.rules,
  },

  // Ignore-comment governance: ban @ts-ignore entirely, require @ts-expect-error to carry a reason.
  // Aligns with the project's "suppress at config level, not inline" policy.
  {
    files: sourceFiles,
    rules: {
      '@typescript-eslint/ban-ts-comment': [
        'error',
        {
          'ts-ignore': false,
          'ts-expect-error': 'allow-with-description',
          'ts-nocheck': false,
          'ts-check': false,
          minimumDescriptionLength: 3,
        },
      ],
    },
  },

  // Register plugins globally (no `files`) so their rules can be referenced downstream.
  // - unicorn: new, not provided by eslint-config-next.
  // - import-x: ESLint 10-compatible fork of eslint-plugin-import. The original
  //   eslint-plugin-import 2.x crashes on ESLint 10 (it calls the removed
  //   SourceCode.getTokenOrCommentBefore inside import/order's fixer), so eslint-plugin-import-x
  //   is used for order / no-cycle / no-default-export rules. eslint-config-next still registers
  //   the original `import` plugin for its own `import/no-anonymous-default-export` rule, which
  //   does not use the removed API and works fine.
  {
    plugins: { unicorn, 'import-x': importX },
  },

  // eslint-plugin-import-x resolver settings (from its typescript flat config).
  // `import-x/resolver: { typescript: true }` resolves `@/*` and `collections/*` path aliases via
  // tsconfig.json through eslint-import-resolver-typescript.
  {
    settings: importX.flatConfigs.typescript.settings,
  },

  // eslint-plugin-import-x rules — scoped to source files only (skip MDX code-block virtual files).
  {
    files: sourceFiles,
    rules: {
      ...importX.flatConfigs.recommended.rules,
      'import-x/order': 'error',
      'import-x/no-cycle': 'error',
    },
  },
  // import-x/no-default-export: off for Next.js pages/layouts/routes/components (default export is
  // the framework convention); on for lib files (no default exports expected there).
  {
    files: ['src/lib/**/*.{ts,tsx}'],
    rules: {
      'import-x/no-default-export': 'error',
    },
  },

  // eslint-plugin-unicorn rules — scoped to source files only.
  {
    files: sourceFiles,
    rules: {
      ...unicorn.configs.recommended.rules,
      // Task-specified rules
      'unicorn/filename-case': [
        'error',
        {
          cases: { kebabCase: true, pascalCase: true },
          // Treat dot-separated parts (e.g. `next.config.mjs`, `foo.test.tsx`) as extensions so
          // only the leading segment is case-checked.
          multipleFileExtensions: true,
          // Don't check directory names — `__tests__` is a standard JS/TS convention (Jest, Vitest).
          checkDirectories: false,
        },
      ],
      // no-array-for-each was renamed to no-for-each in unicorn v71.
      'unicorn/no-for-each': 'warn',
      'unicorn/prefer-set-has': 'warn',
      'unicorn/prefer-optional-catch-binding': 'warn',
      // Rules disabled per task spec or because they conflict with React/Next.js patterns:
      'unicorn/no-null': 'off', // React/Next.js pervasively use null
      'unicorn/prevent-abbreviations': 'off', // too aggressive for this codebase
      'unicorn/consistent-function-scoping': 'off', // flags React handlers / module-local helpers
      'unicorn/no-array-reduce': 'off', // legitimate reduce usage in graph logic
      'unicorn/no-nested-ternary': 'off', // common in JSX conditional rendering
      'unicorn/no-array-callback-reference': 'off', // .map(fn) is readable; style preference
      'unicorn/no-await-expression-member': 'off', // common (await fetch()).json() pattern
      'unicorn/no-instanceof-builtins': 'off', // legitimate instanceof Error checks
      'unicorn/no-object-as-default-parameter': 'off', // common options-bag default pattern
      // name-replacements flags React/Next.js conventions like `props`, `ref`, `docsRoute` — far
      // too aggressive for a React codebase where these are established idioms.
      'unicorn/name-replacements': 'off',
      // consistent-boolean-name requires boolean vars to start with is/has/can etc., but React
      // state naming (mounted, open, loading) and Next.js `revalidate` export convention conflict.
      'unicorn/consistent-boolean-name': 'off',
    },
  },

  // CLI scripts (scripts/*.mts) use process.exit() because ESM loader hooks (register/registerHooks)
  // keep the process alive — without explicit exit, the script hangs after completion.
  // unicorn/no-process-exit and prefer-top-level-await are false positives for this pattern.
  // This block MUST come after the unicorn recommended rules block to override them.
  {
    files: ['scripts/*.mts'],
    rules: {
      'unicorn/no-process-exit': 'off',
      'unicorn/prefer-top-level-await': 'off',
    },
  },

  // Config files legitimately use default imports where named exports also exist
  // (e.g. `tseslint.configs`, `importX.flatConfigs`). These are cautionary warnings, not errors.
  // This block MUST come after the import-x recommended rules block to override them.
  {
    files: ['*.mjs', '*.cjs', 'scripts/*.mts'],
    rules: {
      'import-x/no-named-as-default': 'off',
      'import-x/no-named-as-default-member': 'off',
    },
  },

  // MDX lint layer 1: parse .mdx files + apply mdx/* rules (no-jsx-html-comments, no-unescaped-entities, etc.)
  // mdx.flat is a single config object (files: **/*.{md,mdx}) with its own processor, plugins, and rules.
  mdx.flat,

  // MDX lint layer 2: lint code blocks inside .mdx as real JS/TS/TSX.
  // Scoped to .md/.mdx so the remark processor does not touch real .ts/.tsx files.
  // This overrides mdx.flat's processor for mdx files, enabling lintCodeBlocks.
  {
    files: ['**/*.{md,mdx}'],
    processor: mdx.createRemarkProcessor({
      lintCodeBlocks: true,
    }),
  },

  // Code block rules: turn OFF all react/* and @next/* rules to avoid #89764 crashes on virtual files.
  // mdx.flatCodeBlocks is a single config object scoped to virtual code-block files (**/*.{md,mdx}/**).
  // The rules override block MUST be scoped to the same pattern so that disabling no-undef / no-unused-vars
  // / react / @next rules does not leak into real .ts/.tsx source files.
  mdx.flatCodeBlocks,
  {
    files: ['**/*.{md,mdx}/**'],
    rules: {
      ...mdx.flatCodeBlocks.rules,
      'no-var': 'error',
      'prefer-const': 'error',
      // vercel/next.js#89764: react/* rules crash on ESLint 10 via getFilename()
      'react/display-name': 'off',
      'react/no-direct-mutation-state': 'off',
      'react/no-render-return-value': 'off',
      'react/jsx-key': 'off',
      'react/jsx-no-comment-textnodes': 'off',
      'react/jsx-no-duplicate-props': 'off',
      'react/jsx-no-target-blank': 'off',
      'react/jsx-no-undef': 'off',
      'react/jsx-pascal-case': 'off',
      'react/no-children-prop': 'off',
      'react/no-danger': 'off',
      'react/no-deprecated': 'off',
      'react/no-find-dom-node': 'off',
      'react/no-is-mounted': 'off',
      'react/no-string-refs': 'off',
      'react/no-unescaped-entities': 'off',
      'react/react-in-jsx-scope': 'off',
      'react/require-render-return': 'off',
      'react/rules-of-hooks': 'off',
      'react/self-closing-comp': 'off',
      'react/wrap-multilines': 'off',
      '@next/next/google-font-display': 'off',
      '@next/next/google-font-preconnect': 'off',
      '@next/next/inline-script-id': 'off',
      '@next/next/next-script-for-ga': 'off',
      '@next/next/no-assign-module-variable': 'off',
      '@next/next/no-async-client-component': 'off',
      '@next/next/no-before-interactive-script-outside-document': 'off',
      '@next/next/no-css-tags': 'off',
      '@next/next/no-document-import-in-page': 'off',
      '@next/next/no-duplicate-head': 'off',
      '@next/next/no-head-element': 'off',
      '@next/next/no-head-import-in-document': 'off',
      '@next/next/no-img-element': 'off',
      '@next/next/no-page-custom-font': 'off',
      '@next/next/no-script-component-in-head': 'off',
      '@next/next/no-styled-jsx-in-document': 'off',
      '@next/next/no-sync-server-side-props': 'off',
      '@next/next/no-title-in-document-head': 'off',
      '@next/next/no-typos': 'off',
      '@next/next/no-unwanted-polyfillio': 'off',
      // Disable type-checked rules on virtual code-block files: projectService has no TS project
      // for embedded snippets, so type information is unavailable.
      '@typescript-eslint/no-floating-promises': 'off',
      '@typescript-eslint/no-misused-promises': 'off',
      '@typescript-eslint/require-await': 'off',
      '@typescript-eslint/no-unnecessary-type-assertion': 'off',
      '@typescript-eslint/prefer-optional-chain': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',
    },
  },

  globalIgnores([
    '.next/**',
    'out/**',
    'build/**',
    'coverage/**',
    'next-env.d.ts',
    '.source/**',
  ]),

  // eslint-config-prettier MUST stay LAST to disable formatting rules that conflict with Prettier.
  eslintConfigPrettier,
]);

export default eslintConfig;
