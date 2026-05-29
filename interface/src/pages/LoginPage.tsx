import { useState } from "react";
import { useLocation } from "wouter";
import { useApp, UserRole } from "@/App";
import { login as apiLogin } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { HeartPulse, Stethoscope, User, Moon, Sun, ArrowRight, Settings, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function LoginPage() {
  const { login, theme, toggleTheme } = useApp();
  const [role, setRole] = useState<UserRole | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleRoleSelect = (selectedRole: UserRole) => {
    setRole(selectedRole);
    // Champs toujours vides lors de la sélection d'un rôle
    setUsername("");
    setPassword("");
  };

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [, navigate] = useLocation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!role || !username || !password) {
      setError("Veuillez remplir tous les champs");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await apiLogin(username, password);
      if (response.success) {
        // Passer le rôle et le token au contexte
        login(response.user.role as UserRole, response.user.username, response.token);
        // Redirection vers l'espace approprié
        if (response.user.role === "secretaire") navigate("/secretaire");
        else if (response.user.role === "medical") navigate("/medical");
        else if (response.user.role === "admin") navigate("/admin");
      } else {
        // Identifiants incorrects
        setError("❌ Nom d'utilisateur ou mot de passe incorrect");
      }
    } catch (err: any) {
      setError(err.message || "❌ Échec de l'authentification. Veuillez réessayer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-[100dvh] flex w-full"
      style={{ background: "linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #60a5fa 100%)" }}
    >
      {/* Left Hero Panel */}
      <div className="hidden lg:flex w-1/2 flex-col justify-between p-12 text-white">
        <div
          className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
          onClick={() => setRole(null)}
        >
          <div className="p-2 bg-white/10 rounded-lg">
            <HeartPulse className="w-8 h-8 text-white" />
          </div>
          <span className="text-2xl font-bold tracking-tight">TriageMed AI</span>
        </div>

        <div className="max-w-xl">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-5xl font-extrabold leading-tight mb-6"
          >
            Système de Triage Hospitalier Intelligent
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-lg text-white/80 mb-10"
          >
            Priorisez les patients selon leur gravité et gérez les flux ainsi que les ressources en temps réel.
          </motion.p>
        </div>

        <div className="text-sm text-white/50">
          © {new Date().getFullYear()} TriageMed AI. Tous droits réservés.
        </div>
      </div>

      {/* Right Login Card */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-4xl">
          <Card className="border-white/20 bg-white/95 backdrop-blur-sm shadow-xl rounded-[2rem]">
            <CardHeader className="space-y-1 text-center py-10 px-8">
              <CardTitle className="text-3xl font-bold tracking-tight text-[var(--text-main)]">
                Authentification
              </CardTitle>
              <CardDescription className="text-[var(--text-dimmed)]">
                Sélectionnez votre portail d'accès pour continuer
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">

              {!role ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="grid grid-cols-1 sm:grid-cols-3 gap-6"
                >
                  <Card
                    className="cursor-pointer hover:border-[var(--primary)] transition-all border-[var(--border)] bg-[var(--bg-elevated)] min-h-[220px] rounded-[1.5rem]"
                    onClick={() => handleRoleSelect("secretaire")}
                  >
                    <CardContent className="h-full p-6 flex flex-col items-center justify-center text-center gap-4">
                      <div className="p-3 bg-[var(--primary-soft)] rounded-full text-[var(--primary)]">
                        <User className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-[var(--text-main)]">Espace agent d'accueil</h3>
                      </div>
                    </CardContent>
                  </Card>

                  <Card
                    className="cursor-pointer hover:border-[var(--primary)] transition-all border-[var(--border)] bg-[var(--bg-elevated)] min-h-[220px] rounded-[1.5rem]"
                    onClick={() => handleRoleSelect("medical")}
                  >
                    <CardContent className="h-full p-6 flex flex-col items-center justify-center text-center gap-4">
                      <div className="p-3 bg-[var(--danger-soft)] rounded-full text-[var(--danger)]">
                        <Stethoscope className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-[var(--text-main)]">Staff Médical</h3>
                      </div>
                    </CardContent>
                  </Card>

                  <Card
                    className="cursor-pointer hover:border-[var(--primary)] transition-all border-[var(--border)] bg-[var(--bg-elevated)] min-h-[220px] rounded-[1.5rem]"
                    onClick={() => handleRoleSelect("admin")}
                  >
                    <CardContent className="h-full p-6 flex flex-col items-center justify-center text-center gap-4">
                      <div className="p-3 bg-[var(--warning-soft)] rounded-full text-[var(--warning)]">
                        <Settings className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-[var(--text-main)]">Agent Administratif</h3>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex flex-col md:flex-row gap-8"
                >
                  {/* Left Column: Icon and Role Info */}
                  <div className="w-full md:w-1/3 flex flex-col items-center justify-center text-center gap-4 bg-[var(--bg-inset)] rounded-3xl p-8 border border-[var(--border)]">
                    <div className={`p-4 rounded-full ${role === 'medical' ? 'bg-[var(--danger-soft)] text-[var(--danger)]' : role === 'admin' ? 'bg-[var(--warning-soft)] text-[var(--warning)]' : 'bg-[var(--primary-soft)] text-[var(--primary)]'}`}>
                      {role === "secretaire" ? <User className="w-8 h-8" /> : role === "medical" ? <Stethoscope className="w-8 h-8" /> : <Settings className="w-8 h-8" />}
                    </div>
                    <div>
                      <h3 className="font-semibold text-xl text-[var(--text-main)]">
                        {role === "secretaire" ? "Espace agent d'accueil" : role === "medical" ? "Staff Médical" : "Agent Administratif"}
                      </h3>
                      {role === "secretaire" && (
                        <p className="text-sm text-[var(--text-dimmed)] mt-2 font-medium">(secrétaire)</p>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Login Form */}
                  <div className="w-full md:w-2/3 flex flex-col justify-center relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setRole(null)}
                      className="absolute right-0 -top-4 md:-top-6 text-[var(--text-dimmed)] hover:text-[var(--text-main)]"
                    >
                      Retour
                    </Button>

                    <form onSubmit={handleSubmit} className="space-y-5 pt-6 md:pt-4">
                      {error && (
                        <Alert variant="destructive" className="mb-4">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>{error}</AlertDescription>
                        </Alert>
                      )}

                      <div className="space-y-2">
                        <Label htmlFor="username" className="text-[var(--text-main)] font-medium">Identifiant</Label>
                        <Input
                          id="username"
                          value={username}
                          onChange={(e) => setUsername(e.target.value)}
                          className="bg-[var(--bg-inset)] border-[var(--border)] text-[var(--text-main)] h-11"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="password" className="text-[var(--text-main)] font-medium">Mot de passe</Label>
                        <Input
                          id="password"
                          type="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className="bg-[var(--bg-inset)] border-[var(--border)] text-[var(--text-main)] h-11"
                          required
                        />
                      </div>

                      <Button type="submit" className="w-full bg-[var(--primary)] text-white hover:bg-[var(--primary-h)] h-12 text-base mt-4">
                        Se connecter <ArrowRight className="ml-2 w-5 h-5" />
                      </Button>
                    </form>
                  </div>
                </motion.div>
              )}


            </CardContent>
          </Card>
        </div>
      </div>

      {/* Theme Toggle */}
      <button
        onClick={toggleTheme}
        className="fixed bottom-6 right-6 p-3 rounded-full bg-[var(--bg-elevated)] border border-[var(--border)] text-[var(--text-main)] shadow-lg hover:scale-105 transition-transform"
      >
        {theme === "light" ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
      </button>
    </div>
  );
}
