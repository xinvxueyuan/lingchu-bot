import * as React from "react";
import { cn } from "@/lib/cn";

/**
 * Dependency-free shadcn-style Badge.
 *
 * Reads Starlight theme tokens (--sl-color-*) so it adapts to light/dark mode
 * automatically. Mirrors the visual language of shadcn/ui (new-york) without
 * pulling in @radix-ui/react-slot or class-variance-authority.
 */
type BadgeVariant = "default" | "accent" | "outline" | "destructive";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantClass: Record<BadgeVariant, string> = {
  default:
    "border-transparent bg-[color-mix(in_srgb,var(--sl-color-gray-6)_70%,transparent)] text-[color:var(--sl-color-white)]",
  accent:
    "border-[color-mix(in_srgb,var(--sl-color-accent)_45%,transparent)] bg-[color-mix(in_srgb,var(--sl-color-accent)_18%,transparent)] text-[color:var(--sl-color-accent-high,var(--sl-color-accent))]",
  outline:
    "border-[color-mix(in_srgb,var(--sl-color-gray-4)_60%,transparent)] bg-transparent text-[color:var(--sl-color-gray-2)]",
  destructive:
    "border-[color-mix(in_srgb,var(--sl-color-red,red)_45%,transparent)] bg-[color-mix(in_srgb,var(--sl-color-red,red)_16%,transparent)] text-[color:var(--sl-color-red,#f87171)]",
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      data-slot="badge"
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium leading-4",
        variantClass[variant],
        className,
      )}
      {...props}
    />
  );
}
