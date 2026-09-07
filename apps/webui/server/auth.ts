import { randomUUID } from "node:crypto";
import { SignJWT, jwtVerify, type JWTPayload } from "jose";
import { config } from "./config.js";

/**
 * UBT（WebUI Bearer Token）载荷。
 * 单用户系统：sub 固定为 "root"（用户名锁定 root），并携带 iat / exp / jti。
 */
export interface TokenClaims extends JWTPayload {
  sub: string;
  jti: string;
}

const JWT_TTL = "12h";

// 已吊销的 jti 集合（简单 in-memory，进程内有效）。
const revoked = new Set<string>();

const secret = new TextEncoder().encode(config.jwtSecret);

/** 签发一个新的 UBT。 */
export async function signToken(): Promise<string> {
  const jti = randomUUID();
  return new SignJWT({ sub: "root", jti })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(JWT_TTL)
    .setJti(jti)
    .sign(secret);
}

/**
 * 校验 UBT。校验签名、有效期与吊销集合。
 * 返回载荷或 null（无效 / 已过期 / 已吊销）。
 */
export async function verifyToken(token: string): Promise<TokenClaims | null> {
  try {
    const { payload } = await jwtVerify(token, secret);
    const claims = payload as TokenClaims;
    if (!claims.jti || revoked.has(claims.jti)) return null;
    if (claims.sub !== "root") return null;
    return claims;
  } catch {
    return null;
  }
}

/** 将某个 jti 加入吊销集合。 */
export function revokeToken(jti: string): void {
  revoked.add(jti);
}

/** 从 Authorization 头中提取 Bearer token。 */
export function extractBearer(header: string | undefined): string | null {
  if (!header) return null;
  const match = /^Bearer\s+(.+)$/i.exec(header.trim());
  return match ? match[1].trim() : null;
}
