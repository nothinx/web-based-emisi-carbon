import { createContext, useContext, useState, type ReactNode } from "react";
import { api, getToken, setToken } from "../lib/api";

interface AuthState {
  authed: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthState | null>(null);

// Mode statis (GitHub Pages): tanpa server/login — langsung masuk.
const STATIC = import.meta.env.VITE_STATIC === "1";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authed, setAuthed] = useState(() => STATIC || !!getToken());

  async function login(email: string, password: string) {
    const token = await api.login(email, password);
    setToken(token);
    setAuthed(true);
  }
  function logout() {
    setToken(null);
    setAuthed(false);
  }

  return <Ctx.Provider value={{ authed, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth di luar AuthProvider");
  return v;
}
