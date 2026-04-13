import { Switch, Route, Router as WouterRouter, useLocation } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { createContext, useContext, useState, useEffect } from "react";
import LoginPage from "@/pages/LoginPage";
import PatientPage from "@/pages/PatientPage";
import MedicalPage from "@/pages/MedicalPage";
import NotFound from "@/pages/not-found";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
});

// ── App State ──────────────────────────────────────────────────────────────

export type UserRole = "patient" | "medical" | null;

interface AppContextType {
  role: UserRole;
  username: string;
  theme: "light" | "dark";
  login: (role: UserRole, username: string) => void;
  logout: () => void;
  toggleTheme: () => void;
}

export const AppContext = createContext<AppContextType>({
  role: null,
  username: "",
  theme: "light",
  login: () => {},
  logout: () => {},
  toggleTheme: () => {},
});

export const useApp = () => useContext(AppContext);

// ── Router ─────────────────────────────────────────────────────────────────

function AppRouter() {
  const { role } = useApp();
  const [, navigate] = useLocation();

  useEffect(() => {
    if (!role) navigate("/");
    else if (role === "patient") navigate("/patient");
    else if (role === "medical") navigate("/medical");
  }, [role]);

  return (
    <Switch>
      <Route path="/" component={LoginPage} />
      <Route path="/patient" component={PatientPage} />
      <Route path="/medical" component={MedicalPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

// ── Root ───────────────────────────────────────────────────────────────────

function App() {
  const [role, setRole] = useState<UserRole>(
    () => (localStorage.getItem("triage_role") as UserRole) ?? null
  );
  const [username, setUsername] = useState(
    () => localStorage.getItem("triage_username") ?? ""
  );
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem("triage_theme") as "light" | "dark") ?? "light"
  );

  // Apply theme to root element
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const login = (r: UserRole, u: string) => {
    setRole(r);
    setUsername(u);
    localStorage.setItem("triage_role", r ?? "");
    localStorage.setItem("triage_username", u);
  };

  const logout = () => {
    setRole(null);
    setUsername("");
    localStorage.removeItem("triage_role");
    localStorage.removeItem("triage_username");
  };

  const toggleTheme = () => {
    setTheme((t) => {
      const next = t === "light" ? "dark" : "light";
      localStorage.setItem("triage_theme", next);
      return next;
    });
  };

  return (
    <AppContext.Provider value={{ role, username, theme, login, logout, toggleTheme }}>
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
