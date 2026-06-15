import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";
import "./ui.css";

type Variant = "primary" | "ghost" | "outline" | "danger";

export function Button({
  variant = "outline",
  loading,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return (
    <button className={`btn btn-${variant}`} disabled={rest.disabled || loading} {...rest}>
      {loading ? <span className="spinner" aria-hidden /> : null}
      {children}
    </button>
  );
}

type Tone = "neutral" | "active" | "inactive" | "warn" | "scope1" | "scope2" | "scope3";

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function TierBadge({ tier }: { tier: number }) {
  return (
    <span className={`tier tier-${tier}`} title={tier === 1 ? "Primary / official" : "Secondary"}>
      T{tier}
    </span>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="control" {...props} />;
}

export function Select({ children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className="control" {...rest}>
      {children}
    </select>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="empty">
      <div className="empty-title">{title}</div>
      {hint ? <p className="empty-hint">{hint}</p> : null}
    </div>
  );
}

export function Spinner() {
  return <span className="spinner spinner-dark" aria-label="memuat" />;
}
