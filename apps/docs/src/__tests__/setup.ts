import '@testing-library/jest-dom/vitest';
import { beforeEach, vi } from 'vitest';

// The developer's shell may export `NEXT_PUBLIC_SITE_URL` (e.g. when running
// docs against a custom domain). That bleeds into the default-branch tests
// for `getSiteUrl`/`getSiteMetadata`/RSS, which assume no override. Stub it
// to an empty string before every test so the production fallback path runs;
// individual tests that need to exercise the override branch use
// `vi.stubEnv('NEXT_PUBLIC_SITE_URL', ...)` and `vi.unstubAllEnvs()` in
// `afterEach` reverts the stub.
beforeEach(() => {
  vi.stubEnv('NEXT_PUBLIC_SITE_URL', '');
});
