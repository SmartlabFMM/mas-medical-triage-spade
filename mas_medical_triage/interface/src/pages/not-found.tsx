import { Link } from "wouter";
import { Activity, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-slate-50/30 dark:bg-slate-900/10">
      <div className="max-w-md w-full p-8 bg-card rounded-xl border shadow-sm">
        <div className="mx-auto w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-6">
          <ShieldAlert className="h-8 w-8 text-red-600 dark:text-red-500" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground mb-2">404 - Erreur Système</h1>
        <p className="text-muted-foreground mb-8">
          Le module clinique demandé n'a pas pu être trouvé. Veuillez vérifier l'URL ou retourner au terminal de triage principal.
        </p>
        <Link href="/">
          <Button className="w-full h-12 font-medium flex items-center justify-center gap-2">
            <Activity className="h-4 w-4" />
            Retour au Terminal de Triage
          </Button>
        </Link>
      </div>
    </div>
  );
}
