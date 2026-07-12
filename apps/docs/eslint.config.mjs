import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';
import eslintConfigPrettier from 'eslint-config-prettier';
import * as mdx from 'eslint-plugin-mdx';

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

  // Ignore-comment governance: ban @ts-ignore entirely, require @ts-expect-error to carry a reason.
  // Aligns with the project's "suppress at config level, not inline" policy.
  {
    files: ['**/*.{ts,tsx,mts,cts,js,jsx,mjs,cjs}'],
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
  eslintConfigPrettier,
]);

export default eslintConfig;
