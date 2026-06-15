import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { AppShell } from "./components/AppShell";
import { Login } from "./pages/Login";
import { FactorRegistry } from "./pages/FactorRegistry";
import { Calculator } from "./pages/Calculator";
import { CategoriesPage, GWPPage, SourcesPage } from "./pages/Lookups";

function Protected() {
  const { authed } = useAuth();
  if (!authed) return <Navigate to="/login" replace />;
  return (
    <AppShell>
      <Routes>
        <Route path="/calculator" element={<Calculator />} />
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

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Root />
      </BrowserRouter>
    </AuthProvider>
  );
}
