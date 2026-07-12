import { registerHooks } from 'node:module';
import { register } from 'fumadocs-mdx/node';
import {
    type FileObject,
    type ScanResult,
    printErrors,
    validateFiles,
} from 'next-validate-link';

// Handle image/static asset references that fumadocs-mdx loader cannot process
registerHooks({
    load(url, _context, nextLoad) {
        if (/\.(png|jpe?g|gif|svg|webp|ico|bmp|avif)$/.test(url)) {
            return {
                format: 'module',
                source: 'export default undefined;',
                shortCircuit: true,
            };
        }
        return nextLoad(url, _context);
    },
});

register();

const { source } = await import('../src/lib/source.ts');

type Page = (typeof source)['$inferPage'];

async function main() {
    const scanned = buildScanResult();

    const results = await validateFiles(await getFiles(), {
        scanned,
        markdown: {
            components: {
                Card: { attributes: ['href'] },
            },
        },
        checkRelativePaths: 'as-url',
        determinatePathname(pathname) {
            if (pathname.startsWith('/')) return 'url';
            if (pathname.endsWith('.md') || pathname.endsWith('.mdx')) {
                return 'relative-file-path';
            }
            return 'relative-url';
        },
    });

    printErrors(results, true);

    // Explicitly exit — register() and registerHooks() keep ESM loader hooks
    // alive, preventing Node.js from exiting after the script finishes.
    const hasErrors = results.some(r => r.errors.length > 0);
    process.exit(hasErrors ? 1 : 0);
}

function buildScanResult(): ScanResult {
    const urls: ScanResult['urls'] = new Map();
    const fallbackUrls: ScanResult['fallbackUrls'] = [];

    for (const page of source.getPages()) {
        const hashes = getHeadings(page);
        urls.set(page.url, { hashes });
    }

    return { urls, fallbackUrls };
}

function getHeadings({ data }: Page): string[] {
    return data.toc.map((item: { url: string | string[]; }) => item.url.slice(1));
}

function getFiles() {
    const promises = source.getPages().map(
        async (page): Promise<FileObject> => ({
            path: page.absolutePath,
            content: await page.data.getText('raw'),
            url: page.url,
            data: page.data,
        }),
    );

    return Promise.all(promises);
}

void main().catch(() => process.exit(1));
