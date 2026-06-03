'use client';

import DOMPurify from 'dompurify';
import { use, useId, useSyncExternalStore } from 'react';
import { useTheme } from 'next-themes';

const emptySubscribe = () => () => { };

function useMounted() {
    return useSyncExternalStore(
        emptySubscribe,
        () => true,
        () => false,
    );
}

export function Mermaid({ chart }: { chart: string }) {
    const mounted = useMounted();

    if (!mounted) return;
    return <MermaidContent chart={chart} />;
}

const cache = new Map<string, Promise<unknown>>();

export function getMermaidConfig(resolvedTheme?: string) {
    return {
        startOnLoad: false,
        securityLevel: 'strict' as const,
        htmlLabels: false,
        flowchart: {
            htmlLabels: false,
        },
        fontFamily: 'inherit',
        themeCSS: 'margin: 1.5rem auto 0;',
        theme: resolvedTheme === 'dark' ? 'dark' as const : 'default' as const,
    };
}

export function sanitizeMermaidSvg(svg: string) {
    return DOMPurify.sanitize(svg, {
        RETURN_TRUSTED_TYPE: false,
        USE_PROFILES: { svg: true, svgFilters: true },
        ADD_TAGS: ['style'],
    });
}

export function renderMermaidSvg(
    container: HTMLDivElement,
    sanitizedSvg: string,
    bindFunctions?: (element: Element) => void,
) {
    const svgDocument = new DOMParser().parseFromString(sanitizedSvg, 'image/svg+xml');
    const svgElement = svgDocument.documentElement;
    const hasParserError =
        svgElement.nodeName.toLowerCase() === 'parsererror' ||
        svgDocument.querySelector('parsererror') !== null;
    const isValidSvgRoot = svgElement.namespaceURI === 'http://www.w3.org/2000/svg';

    if (hasParserError || !isValidSvgRoot) {
        container.replaceChildren();
        return;
    }

    container.replaceChildren(container.ownerDocument.importNode(svgElement, true));
    bindFunctions?.(container);
}

function cachePromise<T>(key: string, setPromise: () => Promise<T>): Promise<T> {
    const cached = cache.get(key);
    if (cached) return cached as Promise<T>;

    const promise = setPromise();
    cache.set(key, promise);
    return promise;
}

function MermaidContent({ chart }: { chart: string }) {
    const id = useId();
    const { resolvedTheme } = useTheme();
    const { default: mermaid } = use(cachePromise('mermaid', () => import('mermaid')));

    mermaid.initialize(getMermaidConfig(resolvedTheme));

    const { svg, bindFunctions } = use(
        cachePromise(`${id}-${chart}-${resolvedTheme}`, () => {
            return mermaid.render(id, chart.replaceAll('\\n', '\n'));
        }),
    );
    const sanitizedSvg = sanitizeMermaidSvg(svg);

    return (
        <div
            ref={(container) => {
                if (!container) return;

                renderMermaidSvg(container, sanitizedSvg, bindFunctions);
            }}
        />
    );
}
