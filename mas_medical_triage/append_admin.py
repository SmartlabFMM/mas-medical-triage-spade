# Read the current file
with open(r'c:\Users\MSI\Downloads\mas_medical_triage_spade\mas_medical_triage\interface\src\pages\AdminPage.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Keep lines 0-608 (everything before the first </TabsContent>)
new_lines = lines[:609]

# Add the new content
new_content = '''            </Card>
          </div>
        );
      case "resources":
        return (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold text-slate-900">Gestion des Lits</h2>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="gap-2 bg-blue-900 hover:bg-blue-800">
                    <Plus className="w-4 h-4" />
                    Ajouter un Lit
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Ajouter un nouveau lit</DialogTitle>
                    <DialogDescription>
                      Entrez le nom du lit à ajouter au système.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="resource-name">Nom du lit</Label>
                      <Input
                        id="resource-name"
                        placeholder="Ex: Lit-A16"
                        value={newResourceName}
                        onChange={(e) => setNewResourceName(e.target.value)}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button onClick={handleAddResource} className="bg-blue-900 hover:bg-blue-800">Ajouter</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>

            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nom</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead>Patient Assigné</TableHead>
                      <TableHead>Dernière MàJ</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {resources.map((resource) => (
                      <TableRow key={resource.nom_ressource}>
                        <TableCell className="font-medium">
                          {resource.nom_ressource}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              resource.statut === "disponible"
                                ? "default"
                                : "destructive"
                            }
                            className={
                              resource.statut === "disponible"
                                ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                                : ""
                            }
                          >
                            {resource.statut}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {resource.patient_assigne || (
                            <span className="text-slate-400">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-slate-500">
                          {resource.derniere_maj}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteResource(resource.nom_ressource)}
                            className="text-rose-600 hover:text-rose-700"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        );
      case "doctors":
        return (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold text-slate-900">Gestion des Médecins</h2>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="gap-2 bg-blue-900 hover:bg-blue-800">
                    <Plus className="w-4 h-4" />
                    Ajouter un Médecin
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Ajouter un nouveau médecin</DialogTitle>
                    <DialogDescription>
                      Entrez les informations du médecin.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="doctor-name">Nom</Label>
                      <Input
                        id="doctor-name"
                        placeholder="Ex: Dr. Jean Dupont"
                        value={newDoctorName}
                        onChange={(e) => setNewDoctorName(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="doctor-specialty">Spécialité</Label>
                      <Select
                        value={newDoctorSpecialty}
                        onValueChange={setNewDoctorSpecialty}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Sélectionnez une spécialité" />
                        </SelectTrigger>
                        <SelectContent>
                          {specialties.map((specialty) => (
                            <SelectItem key={specialty} value={specialty}>
                              {specialty}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button onClick={handleAddDoctor} className="bg-blue-900 hover:bg-blue-800">Ajouter</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>

            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Nom</TableHead>
                      <TableHead>Spécialité</TableHead>
                      <TableHead>Disponible</TableHead>
                      <TableHead>Patient</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {doctors.map((doctor) => (
                      <TableRow key={doctor.doctor_id}>
                        <TableCell className="font-mono text-sm">
                          {doctor.doctor_id}
                        </TableCell>
                        <TableCell className="font-medium">{doctor.nom}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{doctor.specialite}</Badge>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleDoctorAvailability(doctor)}
                          >
                            {doctor.disponible.toLowerCase() === "true" ? (
                              <CheckCircle className="w-5 h-5 text-emerald-500" />
                            ) : (
                              <XCircle className="w-5 h-5 text-rose-500" />
                            )}
                          </Button>
                        </TableCell>
                        <TableCell>
                          {doctor.patient_assigne || (
                            <span className="text-slate-400">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteDoctor(doctor.doctor_id)}
                            className="text-rose-600 hover:text-rose-700"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        );
      case "patients":
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-slate-900">Liste des Patients</h2>
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Nom</TableHead>
                      <TableHead>Age</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Médecin</TableHead>
                      <TableHead>Lit</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {patients.map((patient) => (
                      <TableRow key={patient.patient_id}>
                        <TableCell className="font-mono text-xs">
                          {patient.patient_id?.slice(0, 8)}...
                        </TableCell>
                        <TableCell className="font-medium">{patient.nom}</TableCell>
                        <TableCell>{patient.age} ans</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              (patient.score_gravité || 0) <= 25
                                ? "default"
                                : (patient.score_gravité || 0) <= 50
                                ? "secondary"
                                : (patient.score_gravité || 0) <= 75
                                ? "destructive"
                                : "outline"
                            }
                          >
                            {patient.score_gravité?.toFixed(1) || "-"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {patient.action_finale || "en_attente"}
                          </Badge>
                        </TableCell>
                        <TableCell>{patient.medecin_assigne || "-"}</TableCell>
                        <TableCell>{patient.lit_assigne || "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
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
          <h2 className="text-xl font-bold capitalize">{activeTab.replace("_", " ")}</h2>
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

# Combine and write
result = ''.join(new_lines) + new_content

with open(r'c:\Users\MSI\Downloads\mas_medical_triage_spade\mas_medical_triage\interface\src\pages\AdminPage.tsx', 'w', encoding='utf-8') as f:
    f.write(result)

print('File fixed successfully!')
