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

  const body = await renderToReadableStream(
    <ServerRouter context={routerContext} url={request.url} />,
    {
      signal: request.signal,
      onError(error: unknown) {
        responseStatusCode = 500;
        // 构建期错误必须可见：CI 里 console 曾被吞掉，只剩 React Router 的
        // 500 页，无法定位。这里同时写 console 与 stderr（后者更不易丢）。
        const e = error as { message?: string; stack?: string } | undefined;
        const detail = `[webui] prerender error: ${e?.message ?? String(error)}\n${e?.stack ?? ""}`;
        try {
          console.error(detail);
        } catch {
          /* console 被改写时忽略 */
        }
        try {
          const proc = (globalThis as { process?: { stderr?: { write?: (s: string) => void } } })
            .process;
          proc?.stderr?.write?.(`${detail}\n`);
        } catch {
          /* 非 Node 环境忽略 */
        }
      },
    },
  );

  responseHeaders.set("Content-Type", "text/html");
  return new Response(body, {
    status: responseStatusCode,
    headers: responseHeaders,
  });
}
