import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { createContext, useContext, useState, useEffect } from "react";
import LoginPage from "@/pages/LoginPage";
import SecretairePage from "@/pages/SecretairePage";
import MedicalPage from "@/pages/MedicalPage";
import AdminPage from "@/pages/AdminPage";
import NotFound from "@/pages/not-found";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
});

// ── App State ──────────────────────────────────────────────────────────────

export type UserRole = "patient" | "secretaire" | "medical" | "admin" | null;

interface AppContextType {
  role: UserRole;
  username: string;
  theme: "light" | "dark";
  token: string | null;
  login: (role: UserRole, username: string, token?: string) => void;
  logout: () => void;
  toggleTheme: () => void;
}

export const AppContext = createContext<AppContextType>({
  role: null,
  username: "",
  theme: "light",
  token: null,
  login: () => { },
  logout: () => { },
  toggleTheme: () => { },
});

export const useApp = () => useContext(AppContext);

// ── Router ─────────────────────────────────────────────────────────────────

function AppRouter() {
  return (
    <Switch>
      <Route path="/" component={LoginPage} />
      <Route path="/patient" component={SecretairePage} />
      <Route path="/secretaire" component={SecretairePage} />
      <Route path="/medical" component={MedicalPage} />
      <Route path="/admin" component={AdminPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

// ── Root ───────────────────────────────────────────────────────────────────

function App() {
  const [role, setRole] = useState<UserRole>(
    () => (sessionStorage.getItem("triage_role") as UserRole) ?? null
  );
  const [username, setUsername] = useState(
    () => sessionStorage.getItem("triage_username") ?? ""
  );
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem("triage_theme") as "light" | "dark") ?? "light"
  );
  const [token, setToken] = useState<string | null>(
    () => sessionStorage.getItem("triage_token")
  );

  // Apply theme to root element
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const login = (r: UserRole, u: string, tokenValue?: string) => {
    setRole(r);
    setUsername(u);
    if (tokenValue) {
      setToken(tokenValue);
      sessionStorage.setItem("triage_token", tokenValue);
    }
    sessionStorage.setItem("triage_role", r ?? "");
    sessionStorage.setItem("triage_username", u);
  };

  const logout = () => {
    setRole(null);
    setUsername("");
    sessionStorage.removeItem("triage_role");
    sessionStorage.removeItem("triage_username");
    sessionStorage.removeItem("triage_token");
  };

  const toggleTheme = () => {
    setTheme((t) => {
      const next = t === "light" ? "dark" : "light";
      if (role === "patient" || role === "secretaire") {
        const patientName = username || "Patient-Anonyme";
        localStorage.setItem("triage_username", patientName);
      }
      localStorage.setItem("triage_theme", next);
      return next;
    });
  };

  return (
    <AppContext.Provider value={{ role, username, theme, token, login, logout, toggleTheme }}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
            <AppRouter />
          </WouterRouter>
          <Toaster />
        </TooltipProvider>
      </QueryClientProvider>
    </AppContext.Provider>
  );
}

export default App;
