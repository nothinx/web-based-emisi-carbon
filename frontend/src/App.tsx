import { BrowserRouter, HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { AppShell } from "./components/AppShell";
import { Login } from "./pages/Login";
import { FactorRegistry } from "./pages/FactorRegistry";
import { Calculator } from "./pages/Calculator";
import { Organizational } from "./pages/Organizational";
import { Sector } from "./pages/Sector";
import { CategoriesPage, GWPPage, SourcesPage } from "./pages/Lookups";

function Protected() {
  const { authed } = useAuth();
  if (!authed) return <Navigate to="/login" replace />;
  return (
    <AppShell>
      <Routes>
        <Route path="/calculator" element={<Calculator />} />
        <Route path="/organizational" element={<Organizational />} />
        <Route path="/sector" element={<Sector />} />
        <Route path="/factors" element={<FactorRegistry />} />
        <Route path="/sources" element={<SourcesPage />} />
        <Route path="/categories" element={<CategoriesPage />} />
        <Route path="/gwp" element={<GWPPage />} />
        <Route path="*" element={<Navigate to="/calculator" replace />} />
      </Routes>
    </AppShell>
  );
}

function Root() {
  const { authed } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={authed ? <Navigate to="/calculator" replace /> : <Login />} />
      <Route path="/*" element={<Protected />} />
    </Routes>
  );
}

const STATIC = import.meta.env.VITE_STATIC === "1";

export default function App() {
  // Static (GitHub Pages): HashRouter agar deep-link & refresh tak 404.
  const Router = STATIC ? HashRouter : BrowserRouter;
  return (
    <AuthProvider>
      <Router>
        <Root />
      </Router>
    </AuthProvider>
  );
}
