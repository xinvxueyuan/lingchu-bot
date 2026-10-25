import { renderToReadableStream } from "react-dom/server";
import type { EntryContext, RouterContextProvider } from "react-router";
import { ServerRouter } from "react-router";

/**
 * 构建期渲染入口：**只为生成 SPA 的 index.html 兜底外壳**。
 *
 * 运行时（浏览器）不加载本文件；`ssr: false` 下 react-router 只在构建期调用它一次。
 * 因此这里刻意保持最小实现：不引入 `@react-router/node` / `isbot` 等 Node
 * 运行时依赖，也同步 `<html lang>`，避免预渲染文案与客户端首帧不一致。
 */
export default async function handleRequest(
  request: Request,
  responseStatusCode: number,
  responseHeaders: Headers,
  routerContext: EntryContext,
  _loadContext: RouterContextProvider,
): Promise<Response> {
  if (request.method.toUpperCase() === "HEAD") {
    return new Response(null, {
      status: responseStatusCode,
      headers: responseHeaders,
    });
  }

  // 诊断用：prerender 失败时把完整错误打到 stderr（不仅是 console）。
  // CI 里 console.error 曾被吞掉，只剩 React Router 的 500 页，无法定位。
  const dumpError = (stage: string, error: unknown): void => {
    const e = error as { message?: string; stack?: string } | undefined;
    const detail = `[webui] prerender ${stage}: ${e?.message ?? String(error)}\n${e?.stack ?? ""}`;
    try {
      console.error(detail);
    } catch {
      /* console 本身被改写时忽略 */
    }
    try {
      // 不用裸 `process`：避免在无 @types/node 的环境里报 TS2591。
      const proc = (globalThis as { process?: { stderr?: { write?: (s: string) => void } } })
        .process;
      proc?.stderr?.write?.(`${detail}\n`);
    } catch {
      /* 非 Node 环境忽略 */
    }
  };

  let body: ReadableStream<Uint8Array>;
  try {
    body = await renderToReadableStream(
      <ServerRouter context={routerContext} url={request.url} />,
      {
        signal: request.signal,
        onError(error: unknown) {
          responseStatusCode = 500;
          dumpError("onError", error);
        },
      },
    );
  } catch (error) {
    responseStatusCode = 500;
    dumpError("threw", error);
    // 兜底：返回最小 HTML，让构建能继续并暴露问题，而不是只留一个 500 页。
    responseHeaders.set("Content-Type", "text/html");
    return new Response(
      `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>WebUI</title></head><body><div id="root"></div></body></html>`,
      { status: 200, headers: responseHeaders },
    );
  }

  responseHeaders.set("Content-Type", "text/html");
  return new Response(body, {
    status: responseStatusCode,
    headers: responseHeaders,
  });
}
