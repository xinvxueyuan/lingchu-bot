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
        // 构建期错误必须可见，否则只会表现为一个无上下文的 302。
        console.error("[webui] prerender error:", error);
      },
    },
  );

  responseHeaders.set("Content-Type", "text/html");
  return new Response(body, {
    status: responseStatusCode,
    headers: responseHeaders,
  });
}
