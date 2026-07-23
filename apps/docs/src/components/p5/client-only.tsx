"use client";
import { useSyncExternalStore, type ReactNode } from "react";

const emptySubscribe = () => () => {};

interface ClientOnlyProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function ClientOnly({ children, fallback = null }: ClientOnlyProps) {
  const isClient = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
  return isClient ? <>{children}</> : <>{fallback}</>;
}
