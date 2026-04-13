import { useState } from "react";
import { useApp, UserRole } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { HeartPulse, Stethoscope, User, Moon, Sun, ArrowRight, ShieldAlert, Activity, Database } from "lucide-react";
import { motion } from "framer-motion";

export default function LoginPage() {
  const { login, theme, toggleTheme } = useApp();
  const [role, setRole] = useState<UserRole | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleRoleSelect = (selectedRole: UserRole) => {
    setRole(selectedRole);
    if (selectedRole === "patient") {
      setUsername("patient01");
      setPassword("patient123");
    } else {
      setUsername("dr.dupont");
      setPassword("medecin123");
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (role && username) {
      login(role, username);
    }
  };

  return (
    <div className="min-h-[100dvh] flex w-full">
      {/* Left Hero Panel */}
      <div 
        className="hidden lg:flex w-1/2 flex-col justify-between p-12 text-white"
        style={{ background: "linear-gradient(to bottom right, var(--hero-from), var(--hero-to))" }}
      >
        <div className="flex items-center gap-3">
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
            Une plateforme avancée basée sur un système multi-agents BDI pour l'évaluation clinique rapide et la gestion optimale des urgences médicales.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex flex-wrap gap-4"
          >
            <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-full text-sm font-medium border border-white/20">
              <Activity className="w-4 h-4" />
              Analyse BDI temps réel
            </div>
            <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-full text-sm font-medium border border-white/20">
              <ShieldAlert className="w-4 h-4" />
              Protocole FIPA-ACL
            </div>
            <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-full text-sm font-medium border border-white/20">
              <Database className="w-4 h-4" />
              Google Sheets intégré
            </div>
          </motion.div>
        </div>

        <div className="text-sm text-white/50">
          © {new Date().getFullYear()} TriageMed AI. Tous droits réservés.
        </div>
      </div>

      {/* Right Login Card */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-[var(--bg-base)]">
        <div className="w-full max-w-md">
          <Card className="border-[var(--border)] bg-[var(--bg-surface)] shadow-lg">
            <CardHeader className="space-y-1 text-center">
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
                  className="grid grid-cols-1 md:grid-cols-2 gap-4"
                >
                  <Card 
                    className="cursor-pointer hover:border-[var(--primary)] transition-all border-[var(--border)] bg-[var(--bg-elevated)]"
                    onClick={() => handleRoleSelect("patient")}
                  >
                    <CardContent className="p-6 flex flex-col items-center justify-center text-center gap-3">
                      <div className="p-3 bg-[var(--primary-soft)] rounded-full text-[var(--primary)]">
                        <User className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-[var(--text-main)]">Portail Patient</h3>
                        <p className="text-xs text-[var(--text-dimmed)] mt-1">Admission et chat IA</p>
                      </div>
                    </CardContent>
                  </Card>

                  <Card 
                    className="cursor-pointer hover:border-[var(--primary)] transition-all border-[var(--border)] bg-[var(--bg-elevated)]"
                    onClick={() => handleRoleSelect("medical")}
                  >
                    <CardContent className="p-6 flex flex-col items-center justify-center text-center gap-3">
                      <div className="p-3 bg-[var(--danger-soft)] rounded-full text-[var(--danger)]">
                        <Stethoscope className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-[var(--text-main)]">Staff Médical</h3>
                        <p className="text-xs text-[var(--text-dimmed)] mt-1">Gestion des urgences</p>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ) : (
                <motion.form 
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  onSubmit={handleSubmit} 
                  className="space-y-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-[var(--primary)] text-sm font-medium">
                      {role === "patient" ? <User className="w-4 h-4" /> : <Stethoscope className="w-4 h-4" />}
                      <span>{role === "patient" ? "Portail Patient" : "Portail Médical"}</span>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => setRole(null)}
                      className="text-[var(--text-dimmed)] hover:text-[var(--text-main)]"
                    >
                      Retour
                    </Button>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="username" className="text-[var(--text-main)]">Identifiant</Label>
                    <Input 
                      id="username" 
                      value={username} 
                      onChange={(e) => setUsername(e.target.value)}
                      className="bg-[var(--bg-inset)] border-[var(--border)] text-[var(--text-main)]"
                      required
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-[var(--text-main)]">Mot de passe</Label>
                    <Input 
                      id="password" 
                      type="password"
                      value={password} 
                      onChange={(e) => setPassword(e.target.value)}
                      className="bg-[var(--bg-inset)] border-[var(--border)] text-[var(--text-main)]"
                      required
                    />
                  </div>

                  <Button type="submit" className="w-full bg-[var(--primary)] text-white hover:bg-[var(--primary-h)] h-11">
                    Se connecter <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </motion.form>
              )}

              {/* Quick Demo Buttons - Only show on initial state */}
              {!role && (
                <div className="pt-4 border-t border-[var(--border)] flex justify-center gap-4 text-sm text-[var(--text-dimmed)]">
                  Démo rapide: 
                  <button onClick={() => { handleRoleSelect("patient"); setTimeout(() => login("patient", "patient01"), 100); }} className="text-[var(--primary)] hover:underline font-medium">Patient</button>
                  <button onClick={() => { handleRoleSelect("medical"); setTimeout(() => login("medical", "dr.dupont"), 100); }} className="text-[var(--primary)] hover:underline font-medium">Médecin</button>
                </div>
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
