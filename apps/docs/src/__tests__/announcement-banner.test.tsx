import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

const usePathname = vi.fn();

vi.mock('next/navigation', () => ({
  usePathname: () => usePathname(),
}));

import { AnnouncementBanner } from '@/components/announcement-banner';

describe('AnnouncementBanner', () => {
  beforeEach(() => {
    usePathname.mockReset();
  });

  it('should render en message for en locale', () => {
    usePathname.mockReturnValue('/');
    render(<AnnouncementBanner />);
    expect(
      screen.getByText(
        'Lingchu Bot documentation is now live — check it out!',
      ),
    ).toBeInTheDocument();
  });

  it('should render zh message for zh locale', () => {
    usePathname.mockReturnValue('/zh');
    render(<AnnouncementBanner />);
    expect(
      screen.getByText('Lingchu Bot 文档现已上线 — 快来看看吧！'),
    ).toBeInTheDocument();
  });

  it('should render zh message for nested zh paths', () => {
    usePathname.mockReturnValue('/zh/docs/user-guide/commands');
    render(<AnnouncementBanner />);
    expect(
      screen.getByText('Lingchu Bot 文档现已上线 — 快来看看吧！'),
    ).toBeInTheDocument();
  });

  it('should render en message for non-zh paths', () => {
    usePathname.mockReturnValue('/docs/user-guide/commands');
    render(<AnnouncementBanner />);
    expect(
      screen.getByText(
        'Lingchu Bot documentation is now live — check it out!',
      ),
    ).toBeInTheDocument();
  });
});
