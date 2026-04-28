import { Link, NavLink } from "react-router-dom";
import type { PropsWithChildren } from "react";

const links = [
  { to: "/", label: "任务指令台" },
  { to: "/tasks", label: "任务列表" }
];

export function AppLayout({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" to="/">
          <span className="brand-mark">CW</span>
          <div>
            <strong>碰撞预警 Data Agent</strong>
            <small>轨道安全指挥工作台</small>
          </div>
        </Link>
        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>链路</span>
          <strong>解析 · 证据 · 模型 · 报告</strong>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
