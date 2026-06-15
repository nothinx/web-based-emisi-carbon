import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import "./appshell.css";

const STATIC = import.meta.env.VITE_STATIC === "1";

const NAV = [
  { to: "/calculator", label: "Kalkulator Personal", hint: "Hitung jejak karbon", group: "Domain" },
  { to: "/organizational", label: "GHG Organisasi", hint: "Scope 1/2/3 multi-fasilitas", group: "Domain" },
  { to: "/factors", label: "Emission Factors", hint: "Jantung registry", group: "Phase 0 · Core" },
  { to: "/sources", label: "Sources", hint: "Sumber & sitasi", group: "Phase 0 · Core" },
  { to: "/categories", label: "Categories", hint: "Kategori aktivitas", group: "Phase 0 · Core" },
  { to: "/gwp", label: "GWP Sets", hint: "AR4 / AR5 / AR6", group: "Phase 0 · Core" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { logout } = useAuth();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden>
            CO<sub>2</sub>e
          </span>
          <div className="brand-text">
            <strong>Carbon Engine</strong>
            <span>Factor Registry</span>
          </div>
        </div>

        <nav className="nav">
          {NAV.map((n, i) => (
            <div key={n.to} style={{ display: "contents" }}>
              {i === 0 || NAV[i - 1].group !== n.group ? (
                <div className="nav-group">{n.group}</div>
              ) : null}
              <NavLink
                to={n.to}
                className={({ isActive }) => `nav-item${isActive ? " is-active" : ""}`}
              >
                <span className="nav-label">{n.label}</span>
                <span className="nav-hint">{n.hint}</span>
              </NavLink>
            </div>
          ))}
        </nav>

        <div className="sidebar-foot">
          {STATIC ? (
            <span className="static-badge">Demo · berjalan di browser</span>
          ) : (
            <button className="logout" onClick={logout}>
              Keluar
            </button>
          )}
          <span className="reproducible">Reproducible · Traceable</span>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
