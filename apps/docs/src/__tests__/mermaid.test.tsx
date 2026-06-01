import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { getMermaidConfig, Mermaid, sanitizeMermaidSvg } from '@/components/mdx/mermaid';

const mermaidMock = vi.hoisted(() => ({
  initialize: vi.fn(),
  render: vi.fn(() => Promise.resolve({ svg: '<svg><text>test</text></svg>', bindFunctions: vi.fn() })),
}));

vi.mock('next-themes', () => ({
  useTheme: () => ({ resolvedTheme: 'light' }),
}));

vi.mock('mermaid', () => ({
  default: mermaidMock,
}));

describe('Mermaid', () => {
  it('uses strict Mermaid security settings', () => {
    expect(getMermaidConfig('light')).toEqual(
      expect.objectContaining({
        securityLevel: 'strict',
        htmlLabels: false,
        flowchart: { htmlLabels: false },
        theme: 'default',
      }),
    );

    expect(getMermaidConfig('dark')).toEqual(
      expect.objectContaining({
        theme: 'dark',
      }),
    );
  });

  it('sanitizes Mermaid SVG before rendering', () => {
    const sanitizedSvg = sanitizeMermaidSvg(
      '<svg><style>.node{fill:red}</style><script>alert(1)</script><g onclick="alert(1)"><text>safe</text></g></svg>',
    );
    const element = new DOMParser().parseFromString(sanitizedSvg, 'image/svg+xml').documentElement;

    expect(element.querySelector('style')?.textContent).toBe('.node{fill:red}');
    expect(element.querySelector('script')).not.toBeInTheDocument();
    expect(element.querySelector('[onclick]')).not.toBeInTheDocument();
    expect(element.querySelector('text')?.textContent).toBe('safe');
  });

  it('does not render Mermaid content before mount', () => {
    const { container } = render(<Mermaid chart="graph TD; A-->B" />);

    expect(container.innerHTML).toBe('');
    expect(mermaidMock.initialize).not.toHaveBeenCalled();
    expect(mermaidMock.render).not.toHaveBeenCalled();
  });

  it('does not use React raw HTML injection', async () => {
    const { readFile } = await import('node:fs/promises');
    const source = await readFile('src/components/mdx/mermaid.tsx', 'utf8');

    expect(source).not.toContain(['dangerously', 'SetInnerHTML'].join(''));
    expect(source).toContain('replaceChildren');
  });
});
