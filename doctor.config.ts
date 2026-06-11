import type { Config } from "react-doctor";

export default {
  rules: {
    // fumadocs convention: useMDXComponents is exported for MDX provider pattern
    // (providerImportSource). Not currently consumed but required for future auto-resolution.
    "react-doctor/only-export-components": "warn",
    // useMDXComponents is a framework-required re-export, not dead code
    "deslop/unused-export": "off",
  },
} satisfies Config;
