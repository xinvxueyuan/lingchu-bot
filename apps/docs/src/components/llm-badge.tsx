import { Bot } from 'lucide-react';
import { cn } from '@/lib/cn';
import { buttonVariants } from 'fumadocs-ui/components/ui/button';

export function LLMBadge({ locale }: { locale?: string }) {
    const label =
        locale === 'en'
            ? 'AI-friendly docs available via llms.txt'
            : '可通过 llms.txt 获取 AI 友好文档';

    return (
        <a
            href="/llms.txt"
            target="_blank"
            rel="noopener noreferrer"
            aria-label={label}
            title={label}
            className={cn(
                buttonVariants({
                    variant: 'ghost',
                    size: 'icon-xs',
                }),
                'text-fd-muted-foreground hover:text-fd-foreground',
            )}
        >
            <Bot className="size-3.5" />
        </a>
    );
}
