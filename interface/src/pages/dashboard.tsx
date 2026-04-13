import { useListTriageSessions, useGetTriageStats } from "@workspace/api-client-react";
import { format } from "date-fns";
import { Link } from "wouter";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { UrgencyBadge } from "@/components/urgency-badge";
import { Activity, ShieldAlert, CheckCircle2, Clock, Users, ArrowRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useGetTriageStats();
  const { data: sessions, isLoading: sessionsLoading } = useListTriageSessions();

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 bg-slate-50/30 dark:bg-slate-900/10">
      <div className="max-w-6xl mx-auto space-y-8">
        
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Triage Command Center</h1>
          <p className="text-muted-foreground">Overview of active emergency triage sessions.</p>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-l-4 border-l-gray-400">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium">Total Sessions</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {statsLoading ? <Skeleton className="h-8 w-16" /> : <div className="text-3xl font-bold">{stats?.total || 0}</div>}
            </CardContent>
          </Card>
          
          <Card className="border-l-4 border-l-red-500 bg-red-50/30 dark:bg-red-950/10">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium text-red-700 dark:text-red-400">Critical</CardTitle>
              <ShieldAlert className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              {statsLoading ? <Skeleton className="h-8 w-16" /> : <div className="text-3xl font-bold text-red-700 dark:text-red-400">{stats?.critical || 0}</div>}
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-orange-500 bg-orange-50/30 dark:bg-orange-950/10">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium text-orange-700 dark:text-orange-400">High</CardTitle>
              <Activity className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              {statsLoading ? <Skeleton className="h-8 w-16" /> : <div className="text-3xl font-bold text-orange-700 dark:text-orange-400">{stats?.high || 0}</div>}
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-yellow-500 bg-yellow-50/30 dark:bg-yellow-950/10">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium text-yellow-700 dark:text-yellow-400">Medium</CardTitle>
              <Clock className="h-4 w-4 text-yellow-500" />
            </CardHeader>
            <CardContent>
              {statsLoading ? <Skeleton className="h-8 w-16" /> : <div className="text-3xl font-bold text-yellow-700 dark:text-yellow-400">{stats?.medium || 0}</div>}
            </CardContent>
          </Card>
        </div>

        {/* Recent Sessions Table */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Sessions</CardTitle>
            <CardDescription>All triage encounters ordered by recency.</CardDescription>
          </CardHeader>
          <CardContent>
            {sessionsLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : !sessions || sessions.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground flex flex-col items-center">
                <Activity className="h-12 w-12 stroke-[1.5] mb-4 opacity-20" />
                <p>No triage sessions recorded yet.</p>
              </div>
            ) : (
              <div className="rounded-md border">
                <Table>
                  <TableHeader className="bg-slate-50/50 dark:bg-slate-900/50">
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Session ID</TableHead>
                      <TableHead>Urgency</TableHead>
                      <TableHead>Summary</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sessions.map((session) => (
                      <TableRow key={session.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors cursor-pointer group">
                        <TableCell className="font-mono text-xs whitespace-nowrap">
                          {format(new Date(session.createdAt), "MMM d, HH:mm")}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {session.id.substring(0, 8)}...
                        </TableCell>
                        <TableCell>
                          <UrgencyBadge urgency={session.urgency as any} />
                        </TableCell>
                        <TableCell className="max-w-[300px] truncate text-sm">
                          {session.patientSummary || <span className="text-muted-foreground italic">In progress...</span>}
                        </TableCell>
                        <TableCell>
                          {session.isComplete ? (
                            <span className="flex items-center text-xs font-medium text-green-600 dark:text-green-500">
                              <CheckCircle2 className="h-3 w-3 mr-1" /> Complete
                            </span>
                          ) : (
                            <span className="flex items-center text-xs font-medium text-orange-600 dark:text-orange-500">
                              <Activity className="h-3 w-3 mr-1" /> Active
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Link href={`/session/${session.id}`} className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground h-9 w-9 text-muted-foreground opacity-0 group-hover:opacity-100">
                            <ArrowRight className="h-4 w-4" />
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
