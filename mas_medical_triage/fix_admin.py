with open(r'c:\Users\MSI\Downloads\mas_medical_triage_spade\mas_medical_triage\interface\src\pages\AdminPage.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line where we need to start fixing (the duplicate TabsContent)
start_fix = None
for i, line in enumerate(lines):
    if 'TabsContent value="dashboard"' in line and i > 340:
        start_fix = i
        print(f'Found duplicate at line {i+1}')
        break

if start_fix:
    # Keep lines up to but not including the duplicate
    new_lines = lines[:start_fix]
    
    # Now we need to find where the original content ends
    # The original content ends at line 336 with "const renderContent"
    # So we need to remove everything from the duplicate start to where the new renderContent starts
    
    # Find the new renderContent that we added
    render_start = None
    for i, line in enumerate(lines):
        if 'const renderContent = () => {' in line and i < 340:
            render_start = i
            print(f'Found renderContent at line {i+1}')
            break
    
    if render_start:
        # The broken file has:
        # lines 0-render_start-1: good code
        # lines render_start-start_fix-1: our new renderContent (good)
        # lines start_fix-end: old tabs content (bad - needs to be replaced with proper closing)
        
        # Keep the good parts
        new_content = ''.join(lines[:start_fix])
        
        # Add proper closing for renderContent and the return statement
        closing = '''            </div>
          </div>
        );
      case "resources":
        return (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold text-slate-900">Gestion des Lits</h2>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex h-[100dvh] bg-slate-50 overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-slate-900">Admin</h1>
              <p className="text-xs text-slate-500">TriageMed</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          <SidebarItem
            icon={<LayoutDashboard className="w-4 h-4" />}
            label="Tableau de Bord"
            isActive={activeTab === "dashboard"}
            onClick={() => setActiveTab("dashboard")}
          />
          <SidebarItem
            icon={<Bed className="w-4 h-4" />}
            label="Ressources"
            isActive={activeTab === "resources"}
            onClick={() => setActiveTab("resources")}
          />
          <SidebarItem
            icon={<Stethoscope className="w-4 h-4" />}
            label="Médecins"
            isActive={activeTab === "doctors"}
            onClick={() => setActiveTab("doctors")}
          />
          <SidebarItem
            icon={<Users className="w-4 h-4" />}
            label="Patients"
            isActive={activeTab === "patients"}
            onClick={() => setActiveTab("patients")}
          />
        </nav>

        <div className="p-4 border-t border-slate-200">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="w-full justify-start gap-2"
          >
            <LogOut className="w-4 h-4" />
            Déconnexion
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
          <h2 className="text-xl font-bold capitalize">{activeTab.replace('_', ' ')}</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={loadAllData}
            disabled={isLoading}
            className="gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}
'''
        new_content += closing
        
        with open(r'c:\Users\MSI\Downloads\mas_medical_triage_spade\mas_medical_triage\interface\src\pages\AdminPage.tsx', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('File fixed!')
    else:
        print('Could not find renderContent')
else:
    print('Could not find duplicate')
