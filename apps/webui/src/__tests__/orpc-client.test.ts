/**
 * `buildRpcUrl(base)` 契约测试。
 *
 * oRPC 客户端的 URL 派生是「页面能开、API 404」这类漂移的第一道防线：
 * Python 侧由 `services/webui/paths.py` 派生 `{base}/v1/rpc`
 * （`WebuiUrls.rpc_root`），前端必须得出**同一个**字符串。
 *
 * 覆盖三类真实输入形态：
 * - 带尾斜杠的完整前缀（`/lc/webui/`）——配置文件里最常见的手写形态；
 * - 不带尾斜杠（`/lc/webui`）——规范化后的形态；
 * - 明显错配的前缀（`/assets/lc/ui/`）——证明函数只做机械派生、不猜路径。
 *
 * `buildRpcUrl` 归属并行任务产出的 `src/orpc/client.ts`；若该模块尚未落地，
 * 本测试会以模块解析失败报错，属于**依赖未就绪**而非断言失败。
 */

import { describe, expect, it } from "vitest";

import { buildRpcUrl } from "@/orpc/client";

/** oRPC 过程路由相对 base 的固定后缀（与 `paths.WebuiUrls.rpc_root` 一致）。 */
const RPC_SUFFIX = "/v1/rpc";

describe("buildRpcUrl", () => {
  it.each([
    ["/lc/webui/", "/lc/webui/v1/rpc"],
    ["/lc/webui", "/lc/webui/v1/rpc"],
    ["/assets/lc/ui/", "/assets/lc/ui/v1/rpc"],
    ["/assets/lc/ui", "/assets/lc/ui/v1/rpc"],
    ["//lc//webui//", "/lc/webui/v1/rpc"],
  ])("%s → %s", (input, expected) => {
    expect(buildRpcUrl(input)).toBe(expected);
  });

  it.each(["/lc/webui/", "/lc/webui", "/assets/lc/ui/"])(
    "%s 结果以 /v1/rpc 结尾且无重复斜杠",
    (input) => {
      const url = buildRpcUrl(input);
      expect(url.endsWith(RPC_SUFFIX)).toBe(true);
      expect(url).not.toMatch(/\/\//);
    },
  );

  it("所有输入形态收敛到同一结果（幂等）", () => {
    const variants = buildRpcUrl("/lc/webui");
    for (const input of ["/lc/webui/", "/lc/webui", "lc/webui", "/lc//webui/"]) {
      expect(buildRpcUrl(input)).toBe(variants);
    }
  });
});
