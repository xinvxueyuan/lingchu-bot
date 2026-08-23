import * as React from "react";
import { Info, TriangleAlert, CircleCheck } from "lucide-react";
import { cn } from "@/lib/cn";

// Re-export the icons for convenience in case consumers want to override.
export { Info, TriangleAlert, CircleCheck } from "lucide-react";

/**
 * Dependency-free shadcn-style Alert.
 *
 * A presentational callout that complements Starlight's <Aside>. Uses lucide
 * icons (already a dependency) and Starlight theme tokens so it adapts to
 * light/dark mode. Rendered as static HTML by Astro (no client directive
 * needed unless interactive children are added).
 */
type AlertVariant = "default" | "accent" | "destructive";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant;
  icon?: React.ReactNode;
}

const variantWrap: Record<AlertVariant, string> = {
  default:
    "border-[color-mix(in_srgb,var(--sl-color-gray-4)_55%,transparent)] bg-[color-mix(in_srgb,var(--sl-color-bg-nav)_55%,transparent)] text-[var(--sl-color-white)]",
  accent:
    "border-[color-mix(in_srgb,var(--sl-color-accent)_45%,transparent)] bg-[color-mix(in_srgb,var(--sl-color-accent)_10%,transparent)] text-[var(--sl-color-white)]",
  destructive:
    "border-[color-mix(in_srgb,var(--sl-color-red,red)_45%,transparent)] bg-[color-mix(in_srgb,var(--sl-color-red,red)_10%,transparent)] text-[var(--sl-color-white)]",
};

const defaultIcon: Record<AlertVariant, React.ReactNode> = {
  default: <Info className="size-4" />,
  accent: <CircleCheck className="size-4" />,
  destructive: <TriangleAlert className="size-4" />,
};

const iconColor: Record<AlertVariant, string> = {
  default: "text-[var(--sl-color-gray-2)]",
  accent: "text-[var(--sl-color-accent-high,var(--sl-color-accent))]",
  destructive: "text-[var(--sl-color-red,#f87171)]",
};

export function Alert({ className, variant = "default", icon, children, ...props }: AlertProps) {
  return (
    <div
      role="note"
      data-slot="alert"
      className={cn(
        "relative flex gap-3 rounded-lg border p-4 text-sm leading-relaxed shadow-sm",
        variantWrap[variant],
        className,
      )}
      {...props}
    >
      <span
        className={cn("mt-0.5 shrink-0", iconColor[variant])}
        aria-hidden="true"
      >
        {icon ?? defaultIcon[variant]}
      </span>
      <div className="[&>p]:m-0 [&>p+p]:mt-2">{children}</div>
    </div>
  );
}

export function AlertTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h5
      data-slot="alert-title"
      className={cn("mb-1 font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  );
}

export function AlertDescription({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      data-slot="alert-description"
      className={cn("text-[color-mix(in_srgb,var(--sl-color-gray-2)_88%,transparent)]", className)}
      {...props}
    />
  );
}
