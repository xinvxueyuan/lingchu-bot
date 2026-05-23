import { register } from 'fumadocs-mdx/node';
import {
    type FileObject,
    type ScanResult,
    printErrors,
    validateFiles,
} from 'next-validate-link';

register();

const { source } = await import('../src/lib/source.ts');

type Page = (typeof source)['$inferPage'];

async function checkLinks() {
    const scanned = buildScanResult();

    printErrors(
        await validateFiles(await getFiles(), {
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
        }),
        true,
    );
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

void checkLinks();
