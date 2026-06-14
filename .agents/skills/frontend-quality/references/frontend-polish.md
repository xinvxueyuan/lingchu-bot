# Frontend Polish

Use this skill when improving UI for the docs site (`apps/docs`). Preserve the product style, check responsive states, avoid generic layouts, and verify the result visually before handing it back.

## Checklist

### Responsive States

- [ ] Text does not overflow containers on mobile (320px) and desktop (1440px)
- [ ] No overlapping elements at any breakpoint
- [ ] Touch targets are at least 44x44px on mobile
- [ ] Images and media scale properly
- [ ] Navigation collapses gracefully on small screens

### Visual Consistency

- [ ] Spacing follows the project's Tailwind scale (not arbitrary values)
- [ ] Colors use the project's theme tokens, not hardcoded values
- [ ] Typography follows the established hierarchy
- [ ] Interactive elements have consistent hover/focus/active states
- [ ] Loading and empty states are handled

### Layout

- [ ] Content is not too wide or too narrow (max-width constraints)
- [ ] Alignment is consistent (left, center, right)
- [ ] Grid/flex layouts don't break with varying content lengths
- [ ] Scroll behavior is smooth and expected

### Accessibility

- [ ] Color contrast meets WCAG 2.1 AA (4.5:1 for text, 3:1 for large text)
- [ ] Interactive elements are keyboard accessible
- [ ] Focus indicators are visible
- [ ] Alt text on images, aria-labels on icon buttons
- [ ] Heading hierarchy is logical (no skipping levels)

## Project-Specific Notes

- The docs site uses Fumadocs components — prefer them over custom implementations
- Tailwind CSS 4 is used — check Context7 MCP for any API changes from v3
- i18n support (en/zh) — verify layouts work for both languages (CJK text may need different spacing)
