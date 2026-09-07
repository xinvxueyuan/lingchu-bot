/**
 * 登录成功后缓存的唯一密钥（内存，进程内有效）。
 * 与 UBT 同生命周期：进程重启后需重新登录才会恢复转发能力。
 */
let cachedWebuiPassword: string | null = null;

/** 登录校验通过后写入唯一密钥缓存。 */
export function setCachedWebuiPassword(password: string | null): void {
  cachedWebuiPassword = password;
}

/** 读取登录时缓存的唯一密钥（代理转发时附加到上游密码头）。 */
export function getCachedWebuiPassword(): string | null {
  return cachedWebuiPassword;
}
