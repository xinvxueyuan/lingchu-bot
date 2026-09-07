import type { SimpleIcon } from "simple-icons";

interface IconProps {
  icon: SimpleIcon;
  size?: number;
  className?: string;
  title?: string;
}

export function Icon({ icon, size = 24, className, title }: IconProps) {
  return (
    <svg
      role="img"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="currentColor"
      className={className}
      aria-label={title ?? icon.title}
      aria-hidden={title ? undefined : true}
    >
      {title ? <title>{title}</title> : null}
      <path d={icon.path} />
    </svg>
  );
}
