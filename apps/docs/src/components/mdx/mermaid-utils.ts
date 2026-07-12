import DOMPurify from "dompurify";

export function getMermaidConfig(resolvedTheme?: string) {
  return {
    startOnLoad: false,
    securityLevel: "strict" as const,
    htmlLabels: false,
    flowchart: {
      htmlLabels: false,
    },
    fontFamily: "inherit",
    themeCSS: "margin: 1.5rem auto 0;",
    theme: resolvedTheme === "dark" ? ("dark" as const) : ("default" as const),
  };
}

export function sanitizeMermaidSvg(svg: string) {
  return DOMPurify.sanitize(svg, {
    RETURN_TRUSTED_TYPE: false,
    USE_PROFILES: { svg: true, svgFilters: true },
    ADD_TAGS: ["style"],
  });
}

export function renderMermaidSvg(
  container: HTMLDivElement,
  sanitizedSvg: string,
  bindFunctions?: (element: Element) => void,
) {
  const svgDocument = new DOMParser().parseFromString(sanitizedSvg, "image/svg+xml");
  const svgElement = svgDocument.documentElement;
  const hasParserError =
    svgElement.nodeName.toLowerCase() === "parsererror" ||
    svgDocument.querySelector("parsererror") !== null;
  const isValidSvgRoot = svgElement.namespaceURI === "http://www.w3.org/2000/svg";

  if (hasParserError || !isValidSvgRoot) {
    container.replaceChildren();
    return;
  }

  container.replaceChildren(container.ownerDocument.importNode(svgElement, true));
  bindFunctions?.(container);
}
