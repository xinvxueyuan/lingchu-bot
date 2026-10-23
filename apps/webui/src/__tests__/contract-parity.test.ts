/**
 * oRPC 契约等价性断言（迁移前后数据结构不变的机械证明）。
 *
 * 迁移把「前端 → Node 后端 → NoneBot」的三层链路收敛为「前端 → NoneBot 同进程
 * oRPC」，代价是响应结构从两处手写变成一处手写 + 一处契约。本测试用 Zod
 * schema 把「结构等价」变成断言，而不是靠人工比对：
 *
 * - 全字段响应可解析；
 * - `errors` 接受任意字符串值（错误码会随上游失败形态演进，不能收窄成枚举）；
 * - 除 `errors` 外的可选块缺失仍可解析——但 `errors` 必须存在，
 *   否则前端 `isOnebotDisconnected()` 的 `.errors.xxx` 访问会直接抛错。
 *
 * `contract` 归属并行任务产出的 `src/orpc/contract.ts`；若该模块尚未落地，
 * 本测试会以模块解析失败报错，属于**依赖未就绪**而非断言失败。
 */

import { describe, expect, it } from "vitest";

import { overviewOutputSchema } from "@/orpc/contract";

/** 全字段响应：五个 OneBot 区块 + 版本号 + 空错误集合。 */
const FULL_RESPONSE = {
  loginInfo: { user_id: 10001, nickname: "灵初" },
  status: { online: true, good: true },
  versionInfo: { app_name: "NapCat", app_version: "4.0.0" },
  groups: [{ group_id: 87654321, group_name: "测试群" }],
  friends: [{ user_id: 10002, nickname: "好友" }],
  lingchuVersion: "0.9.0",
  errors: {},
} as const;

describe("overview 输出契约", () => {
  it("全字段响应可解析", () => {
    const parsed = overviewOutputSchema.parse(FULL_RESPONSE);
    expect(parsed.loginInfo?.user_id).toBe(10001);
    expect(parsed.groups?.[0]?.group_id).toBe(87654321);
    expect(parsed.errors).toEqual({});
  });

  it("errors 允许任意字符串值", () => {
    // 错误码是开放集合：已知的 onebot_disconnected / unavailable 与未知码都必须通过，
    // 否则后端一旦新增失败形态，前端就会在解析阶段崩掉。
    const codes = ["onebot_disconnected", "unavailable", "upstream_error"];
    const parsed = overviewOutputSchema.parse({
      errors: {
        loginInfo: codes[0],
        status: codes[1],
        versionInfo: codes[2],
        groups: codes[0],
        friends: codes[1],
      },
    });
    expect(parsed.errors.loginInfo).toBe("onebot_disconnected");
    expect(Object.keys(parsed.errors)).toHaveLength(5);
  });

  it("可用任意字符串值填充 errors 的键", () => {
    // 并不存在错误码枚举；任何字符串都可作为值出现。
    expect(() =>
      overviewOutputSchema.parse({ errors: { somethingNew: "future_code" } }),
    ).not.toThrow();
  });

  it("可选块缺失仍可解析", () => {
    const parsed = overviewOutputSchema.parse({ errors: {} });
    expect(parsed.loginInfo).toBeUndefined();
    expect(parsed.status).toBeUndefined();
    expect(parsed.versionInfo).toBeUndefined();
    expect(parsed.groups).toBeUndefined();
    expect(parsed.friends).toBeUndefined();
    expect(parsed.lingchuVersion).toBeUndefined();
  });

  it("仅 lingchuVersion + errors 的降级响应仍可解析", () => {
    const parsed = overviewOutputSchema.parse({
      errors: { loginInfo: "onebot_disconnected" },
      lingchuVersion: "0.9.0",
    });
    expect(parsed.lingchuVersion).toBe("0.9.0");
    expect(parsed.errors.loginInfo).toBe("onebot_disconnected");
  });

  it("errors 缺失必须解析失败（fail-loud 契约）", () => {
    // 这一条是保护前端而存在的：errors 缺失时 isOnebotDisconnected() 会抛 TypeError，
    // 契约层必须先拒绝，而不是把坏数据放进渲染树。
    expect(() => overviewOutputSchema.parse({ lingchuVersion: "0.9.0" })).toThrow();
  });
});
