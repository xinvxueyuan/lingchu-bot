import { cn } from "@/lib/utils";

/** 圆形头像：统一边框与对象裁切；size 传入 Tailwind 尺寸类（默认 size-8）。 */
export function Avatar({
  src,
  alt,
  size = "size-8",
  className,
}: {
  src: string;
  alt: string;
  size?: string;
  className?: string;
}) {
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      className={cn("shrink-0 rounded-full border border-border object-cover", size, className)}
    />
  );
}
