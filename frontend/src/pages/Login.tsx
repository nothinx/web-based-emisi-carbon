import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { api, ApiError } from "../lib/api";
import { Button, Field, Input } from "../components/ui";
import "./login.css";

export function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "register") {
        await api.register(email, password);
      }
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal masuk");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-aside">
        <div className="login-mark" aria-hidden>
          CO<sub>2</sub>e
        </div>
        <h1>Carbon Emission Engine</h1>
        <p>
          Perhitungan emisi tingkat penelitian — <em>reproducible</em>,{" "}
          <em>traceable</em>, dan sadar-ketidakpastian. Masuk untuk mengelola Factor
          Registry.
        </p>
        <ul className="login-points">
          <li>Snapshot faktor beku per hasil</li>
          <li>Versi faktor yang dapat diaudit</li>
          <li>Faktor lokal Indonesia diprioritaskan</li>
        </ul>
      </div>

      <form className="login-card" onSubmit={submit}>
        <h2>{mode === "login" ? "Masuk" : "Daftar"}</h2>
        <Field label="Email">
          <Input
            type="email"
            value={email}
            autoComplete="username"
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Field>
        <Field label="Password" hint="Minimal 8 karakter untuk akun baru.">
          <Input
            type="password"
            value={password}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        {error ? <div className="login-error">{error}</div> : null}
        <Button variant="primary" type="submit" loading={busy}>
          {mode === "login" ? "Masuk" : "Daftar & Masuk"}
        </Button>
        <button
          type="button"
          className="login-switch"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Belum punya akun? Daftar" : "Sudah punya akun? Masuk"}
        </button>
      </form>
    </div>
  );
}
