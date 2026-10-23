/**
 * WebUI oRPC 契约（契约优先的单一接口真相源）。
 *
 * 每个过程与 Python 侧 `services/webui/orpc.py` 的 `build_procedure_routes` 一一对应：
 * 路径全部相对于 `{base}/v1/rpc`，方法、输入、输出必须两端同步修改。
 *
 * Python 侧的响应约定（`_ok` / `_error`）与 oRPC RPC 协议一致：
 * 成功 `{"json": ...}`，业务错误 `{"error": {"code", "message", "data"}}` 且 HTTP 200；
 * 仅鉴权失败保持 HTTP 401，供 `client.ts` 统一拦截跳登录页。
 *
 * 禁止使用 `z.any()`：输出结构一旦退化为 any，契约就失去了校验与类型推导的意义。
 */

import { oc } from "@orpc/contract";
import { z } from "zod";

/** OneBot `get_status` 中前端展示的字段。 */
const OnebotStatusSchema = z.object({
  online: z.boolean().optional(),
  good: z.boolean().optional(),
});

/** OneBot `get_login_info` 返回值。 */
const LoginInfoSchema = z.object({
  user_id: z.number(),
  nickname: z.string(),
});

/** OneBot `get_version_info` 中前端展示的字段。 */
const VersionInfoSchema = z.object({
  app_name: z.string().optional(),
  app_version: z.string().optional(),
});

/** OneBot `get_group_list` 数组元素。 */
const GroupInfoSchema = z.object({
  group_id: z.number(),
  group_name: z.string().optional(),
});

/** OneBot `get_friend_list` 数组元素。 */
const FriendInfoSchema = z.object({
  user_id: z.number(),
  nickname: z.string().optional(),
});

/**
 * 概览聚合载荷，严格对应旧 `overview-api.ts` 的 `OverviewData`。
 *
 * `errors` 为必填：键存在（值为错误码）即表示该区块请求失败，
 * 前端据此逐区块渲染独立错误态；空对象表示全部成功。
 */
export const OverviewSchema = z.object({
  loginInfo: LoginInfoSchema.optional(),
  status: OnebotStatusSchema.optional(),
  versionInfo: VersionInfoSchema.optional(),
  groups: GroupInfoSchema.array().optional(),
  friends: FriendInfoSchema.array().optional(),
  lingchuVersion: z.string().optional(),
  errors: z.record(z.string(), z.string()),
});

export type Overview = z.infer<typeof OverviewSchema>;

/** 概览输出 schema 的稳定公开名（测试与外部消费方防止改名漂移）。 */
export const overviewOutputSchema = OverviewSchema;

/** QQ 号合法形态：4~15 位数字（与 Python 侧 `_QQ_ID_MIN_LENGTH` / `_QQ_ID_MAX_LENGTH` 一致）。 */
const QQ_ID_PATTERN = /^\d{4,15}$/;

/** `get_cookies` 透传的上游结果：形状由 OneBot 实现决定，仅约束为对象。 */
const CookiesSchema = z.object({
  cookies: z.string().optional(),
  bkn: z.number().optional(),
});

/** `get_csrf_token` 透传的上游结果。 */
const CsrfTokenSchema = z.object({
  token: z.number().optional(),
});

export const contract = {
  auth: {
    /** 口令换取 HttpOnly 会话 Cookie；口令错误返回 401。 */
    login: oc
      .route({ method: "POST", path: "/auth/login" })
      .input(z.object({ password: z.string().min(1) }))
      .output(z.object({ ok: z.literal(true), expiresAt: z.number() })),
    /** 清除会话 Cookie。 */
    logout: oc
      .route({ method: "POST", path: "/auth/logout" })
      .output(z.object({ ok: z.literal(true) })),
    /** 当前会话信息；未登录返回 401。 */
    me: oc
      .route({ method: "GET", path: "/auth/me" })
      .output(z.object({ sub: z.literal("root"), expiresAt: z.number() })),
  },
  /**
   * 概览聚合：一次性返回 OneBot 只读信息，失败区块记入 `errors`。
   *
   * 必须是**顶层扁平过程**（调用形态 `client.overview()`）。oRPC 的客户端按
   * 路由键路径拼 URL，嵌套写法 `overview: { get }` 会请求 `/v1/rpc/overview/get`，
   * 与 Python 侧注册的 `/v1/rpc/overview` 不一致。
   */
  overview: oc.route({ method: "GET" }).output(OverviewSchema),
  onebot: {
    loginInfo: oc
      .route({ method: "GET", path: "/onebot/login-info" })
      .output(z.object({ user_id: z.number(), nickname: z.string() })),
    status: oc
      .route({ method: "GET", path: "/onebot/status" })
      .output(
        z.object({
          online: z.boolean().optional(),
          good: z.boolean().optional(),
        }),
      ),
    versionInfo: oc
      .route({ method: "GET", path: "/onebot/version-info" })
      .output(VersionInfoSchema),
    groups: oc
      .route({ method: "GET", path: "/onebot/groups" })
      .output(GroupInfoSchema.array()),
    friends: oc
      .route({ method: "GET", path: "/onebot/friends" })
      .output(FriendInfoSchema.array()),
    /** 按 QQ 号取昵称；查不到返回 not_found。 */
    stranger: oc
      .route({ method: "GET", path: "/onebot/stranger" })
      .input(z.object({ qq: z.string().regex(QQ_ID_PATTERN) }))
      .output(z.object({ qq: z.string(), nickname: z.string() })),
    /** 透传 `get_cookies`，可选 domain。 */
    cookies: oc
      .route({ method: "GET", path: "/onebot/cookies" })
      .input(z.object({ domain: z.string().optional() }))
      .output(CookiesSchema),
    /** 透传 `get_csrf_token`。 */
    csrfToken: oc
      .route({ method: "GET", path: "/onebot/csrf-token" })
      .output(CsrfTokenSchema),
  },
  system: {
    /** 插件自产状态。 */
    status: oc.route({ method: "GET", path: "/system/status" }).output(
      z.object({
        status: z.string(),
        plugin: z.string(),
        version: z.string(),
      }),
    ),
    /** 插件自产基本信息。 */
    info: oc.route({ method: "GET", path: "/system/info" }).output(
      z.object({
        name: z.string(),
        description: z.string(),
        version: z.string(),
      }),
    ),
  },
};

export type Contract = typeof contract;
