import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface ShadcnDialogDemoProps {
  trigger?: string;
  title?: string;
  description?: string;
}

export function ShadcnDialogDemo({
  trigger = "Open Dialog",
  title = "Theme Bridge Works",
  description = "This dialog uses shadcn tokens (--color-background, --color-foreground) bridged from Starlight theme variables via @theme inline.",
}: ShadcnDialogDemoProps) {
  return (
    <Dialog>
      <DialogTrigger>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
      </DialogContent>
    </Dialog>
  );
}
