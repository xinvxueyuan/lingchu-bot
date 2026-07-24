import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";

/**
 * Static showcase of the shadcn-style Badge and Alert components.
 * Rendered server-side (no client directive needed).
 */
export function BadgeAlertDemo() {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>default</Badge>
        <Badge variant="accent">accent</Badge>
        <Badge variant="outline">outline</Badge>
        <Badge variant="destructive">deprecated</Badge>
        <Badge variant="accent">v1.0.0</Badge>
      </div>

      <Alert variant="accent">
        <AlertTitle>Adapter selected</AlertTitle>
        <AlertDescription>
          OneBot V11 is the default and only active adapter. Switching is explicit through{" "}
          <code>LINGCHUAdapter</code>.
        </AlertDescription>
      </Alert>

      <Alert variant="destructive">
        <AlertTitle>Deprecated adapters</AlertTitle>
        <AlertDescription>
          Milky, QQ, and OneBot V12 are deprecated and fully removed. Configuring any of them exits
          with a clear <code>PlatformAdapterUnknownError</code>.
        </AlertDescription>
      </Alert>
    </div>
  );
}
