import { Navigate } from "react-router";

/** 旧 /config 占位页已拆分为「基本配置 / 高级配置」两个子页，此处 302 级重定向。 */
export default function Config() {
  return <Navigate to="/config/basic" replace />;
}
