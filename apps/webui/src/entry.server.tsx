import { renderToReadableStream } from "react-dom/server";
import type { EntryContext, RouterContextProvider } from "react-router";
import { ServerRouter } from "react-router";
import { isbot } from "isbot";

import i18n from "@/i18n";

const SUPPORTED_LNGS = ["zh-CN", "en-US"] as const;
const DEFAULT_LNG = "zh-CN";

/**
 * 解析 Cookie 中指定名称的值（用于读取 lingchu-lng）。
 */
function getCookie(name: string, cookieHeader: string | null): string | undefined {
  if (!cookieHeader) return undefined;
  for (const part of cookieHeader.split(";")) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    const key = part.slice(0, eq).trim();
    if (key !== name) continue;
    const value = part.slice(eq + 1).trim();
    try {
      return decodeURIComponent(value);
    } catch {
      return value;
    }
  }
  return undefined;
}

/**
 * Accept-Language 最佳匹配：按 q 值降序，先做大小写归一后的精确匹配，
 * 再按基础语言（如 "zh" → "zh-CN"、"en" → "en-US"）匹配受支持语言。
 */
function matchAcceptLanguage(header: string): string | undefined {
  const entries = header
    .split(",")
    .map((part) => {
      const [tag, ...params] = part.trim().split(";");
      const qParam = params.find((p) => p.trim().toLowerCase().startsWith("q="));
      const q = qParam ? Number(qParam.trim().slice(2)) : 1;
      return { tag: tag.trim().toLowerCase(), q: Number.isFinite(q) ? q : 0 };
    })
    .filter((entry) => entry.tag.length > 0 && entry.q > 0)
    .sort((a, b) => b.q - a.q);

  for (const { tag } of entries) {
    // 精确匹配（大小写归一后比对）
    const exact = SUPPORTED_LNGS.find((lng) => lng.toLowerCase() === tag);
    if (exact) return exact;
    // 基础语言匹配：如 "zh" → "zh-CN"、"en" → "en-US"
    const base = tag.split("-")[0];
    const byBase = SUPPORTED_LNGS.find((lng) => lng.toLowerCase().split("-")[0] === base);
    if (byBase) return byBase;
  }
  return undefined;
}

/**
 * 解析请求语言：① Cookie lingchu-lng → ② Accept-Language 最佳匹配 → ③ 回退 zh-CN。
 */
function resolveLanguage(request: Request): string {
  const cookieLng = getCookie("lingchu-lng", request.headers.get("cookie"));
  if (cookieLng && SUPPORTED_LNGS.includes(cookieLng as (typeof SUPPORTED_LNGS)[number])) {
    return cookieLng;
  }
  const acceptLng = request.headers.get("accept-language");
  if (acceptLng) {
    const matched = matchAcceptLanguage(acceptLng);
    if (matched) return matched;
  }
  return DEFAULT_LNG;
}

export default async function handleRequest(
  request: Request,
  responseStatusCode: number,
  responseHeaders: Headers,
  routerContext: EntryContext,
  _loadContext: RouterContextProvider,
): Promise<Response> {
  // HEAD 请求不携带 body（RFC 9110）
  if (request.method.toUpperCase() === "HEAD") {
    return new Response(null, {
      status: responseStatusCode,
      headers: responseHeaders,
    });
  }

  // 渲染前把请求语言同步到 i18n 单例，
  // 保证 <html lang> 与页面文案均使用该语言（SSR 首屏语言一致）。
  const lng = resolveLanguage(request);
  if (lng !== i18n.resolvedLanguage) {
    await i18n.changeLanguage(lng);
  }

  let shellRendered = false;
  const body = await renderToReadableStream(
    <ServerRouter context={routerContext} url={request.url} />,
    {
      signal: request.signal,
      onError(error: unknown) {
        responseStatusCode = 500;
        // 仅记录流式渲染阶段（shell 之外）的错误；
        // shell 渲染错误会直接 reject 并交由上层处理。
        if (shellRendered) {
          console.error(error);
        }
      },
    },
  );
  shellRendered = true;

  // 机器人/爬虫等待全部内容就绪后再响应，保证 SEO 抓取到完整 HTML；
  // 普通请求直接返回已开始的流，首屏更快。
  const userAgent = request.headers.get("user-agent");
  if (userAgent && isbot(userAgent)) {
    await body.allReady;
  }

  responseHeaders.set("Content-Type", "text/html");
  return new Response(body, {
    status: responseStatusCode,
    headers: responseHeaders,
  });
}
