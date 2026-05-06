import { Link } from "wouter";
import { Activity, LayoutDashboard } from "lucide-react";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 border-r bg-card flex flex-col justify-between hidden md:flex">
        <div>
          <div className="h-16 flex items-center px-6 border-b">
            <Activity className="h-6 w-6 text-primary mr-2" />
            <span className="font-semibold text-lg tracking-tight">Triage AI</span>
          </div>
          <nav className="p-4 space-y-2">
            <Link 
              href="/" 
              className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-accent text-sm font-medium transition-colors"
            >
              <Activity className="h-4 w-4" />
              New Triage
            </Link>
            <Link 
              href="/dashboard" 
              className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-accent text-sm font-medium transition-colors"
            >
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </Link>
          </nav>
        </div>
        <div className="p-4 border-t text-xs text-muted-foreground">
          <p>Secure Medical Network</p>
          <p>ED-Terminal 04</p>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Mobile Header */}
        <div className="md:hidden h-14 border-b bg-card flex items-center px-4 justify-between shrink-0">
          <div className="flex items-center">
            <Activity className="h-5 w-5 text-primary mr-2" />
            <span className="font-semibold">Triage AI</span>
          </div>
          <div className="flex space-x-4 text-sm font-medium">
            <Link href="/" className="hover:text-primary transition-colors">Chat</Link>
            <Link href="/dashboard" className="hover:text-primary transition-colors">Dashboard</Link>
          </div>
        </div>
        
        {children}
      </main>
    </div>
  );
}
