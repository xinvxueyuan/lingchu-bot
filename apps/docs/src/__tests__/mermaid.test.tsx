import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { Mermaid } from '@/components/mdx/mermaid';

vi.mock('next-themes', () => ({
  useTheme: () => ({ resolvedTheme: 'light' }),
}));

vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(() => Promise.resolve({ svg: '<svg>test</svg>', bindFunctions: vi.fn() })),
  },
}));

describe('Mermaid', () => {
  it('should return null on server side (not mounted)', () => {
    const { container } = render(<Mermaid chart="graph TD; A-->B" />);
    expect(container.innerHTML).toBe('');
  });

  it('should accept chart prop', () => {
    const chart = 'graph TD; A-->B; A-->C';
    const { container } = render(<Mermaid chart={chart} />);
    expect(container).toBeDefined();
  });
});
