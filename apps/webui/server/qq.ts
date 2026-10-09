/**
 * QQ 头像获取（依据腾讯云开发者社区文章集成）：
 * https://cloud.tencent.com/developer/article/2173804
 *
 * 头像使用公共 CDN（q.qlogo.cn），无需登录，可直接取图。
 * 昵称不再在此处直连 qzone（匿名调用返回 need login），改由 nonebot 侧
 * get_stranger_info 端点提供，经 WebUI 代理中间件转发。
 */

const QQ_AVATAR_BASE = "https://q.qlogo.cn/headimg_dl";

/**
 * 构造 QQ 头像 URL（公共 CDN，无需登录）。
 *
 * @param qq QQ 号
 * @param spec 规格：1/2/3→40px，4→140px，5→640px（亦可传 100 等）
 */
export function getQQAvatarUrl(qq: string, spec = 100): string {
  const uin = encodeURIComponent(qq);
  return `${QQ_AVATAR_BASE}?dst_uin=${uin}&spec=${spec}&img_type=jpg`;
}
