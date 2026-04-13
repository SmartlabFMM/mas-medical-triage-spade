import { useGetTriageSession } from "@workspace/api-client-react";
import { useParams, Link } from "wouter";
import { format } from "date-fns";
import { ArrowLeft, User, Activity, HeartPulse, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { UrgencyBadge } from "@/components/urgency-badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { ExtractedData } from "@workspace/api-client-react/src/generated/api.schemas";

export default function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  
  const { data, isLoading, error } = useGetTriageSession(sessionId || "", {
    query: { enabled: !!sessionId }
  });

  if (isLoading) {
    return (
      <div className="p-8 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-[500px] lg:col-span-2" />
          <Skeleton className="h-[500px]" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
        <Activity className="h-12 w-12 text-muted-foreground/30 mb-4" />
        <h2 className="text-xl font-semibold mb-2">Session Not Found</h2>
        <p className="text-muted-foreground mb-6">This triage session could not be retrieved.</p>
        <Link href="/dashboard" className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const { session, messages } = data;
  
  // Find the last assistant message with extracted data for the final state
  const finalExtractedData = messages
    .filter(m => m.role === "assistant" && m.extractedData)
    .pop()?.extractedData as ExtractedData | undefined;

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 bg-slate-50/30 dark:bg-slate-900/10">
      <div className="max-w-6xl mx-auto space-y-6">
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="outline" size="icon" className="h-9 w-9">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Session Review</h1>
              <p className="text-sm font-mono text-muted-foreground">ID: {session.id}</p>
            </div>
          </div>
          <UrgencyBadge urgency={session.urgency as any} className="px-4 py-1 text-sm shadow-sm" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Message History */}
          <Card className="lg:col-span-2 flex flex-col h-[70vh] shadow-sm border-border/60">
            <CardHeader className="py-4 border-b bg-slate-50/50 dark:bg-slate-900/50">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <FileText className="h-4 w-4" /> Transcript
              </CardTitle>
              <CardDescription>
                Started {format(new Date(session.createdAt), "MMM d, yyyy HH:mm")}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/30 dark:bg-slate-900/10">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <Activity className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  
                  <div className="flex flex-col gap-1 max-w-[80%]">
                    <span className={`text-[10px] uppercase font-semibold text-muted-foreground ${msg.role === "user" ? "text-right" : "text-left"}`}>
                      {msg.role === "user" ? "Patient" : "AI Nurse"} • {format(new Date(msg.createdAt), "HH:mm")}
                    </span>
                    <div 
                      className={`px-4 py-3 rounded-lg shadow-sm ${
                        msg.role === "user" 
                          ? "bg-primary text-primary-foreground rounded-tr-sm" 
                          : "bg-card border rounded-tl-sm text-foreground"
                      }`}
                    >
                      <p className="text-sm leading-relaxed">{msg.content}</p>
                    </div>
                  </div>

                  {msg.role === "user" && (
                    <div className="h-8 w-8 rounded-full bg-secondary border flex items-center justify-center shrink-0">
                      <User className="h-4 w-4 text-muted-foreground" />
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Extracted Data Summary */}
          <Card className="shadow-sm border-border/60 flex flex-col h-[70vh]">
            <CardHeader className="py-4 border-b bg-slate-50/50 dark:bg-slate-900/50 shrink-0">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <HeartPulse className="h-4 w-4" /> Final Assessment
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-6">
              {finalExtractedData ? (
                <div className="space-y-6">
                  {/* Status */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Conscious</span>
                      <p className={`font-semibold ${finalExtractedData.is_conscious ? "text-green-600 dark:text-green-500" : "text-red-600 dark:text-red-500"}`}>
                        {finalExtractedData.is_conscious ? "YES" : "NO"}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Status</span>
                      <p className="font-semibold text-foreground">
                        {session.isComplete ? "Complete" : "In Progress"}
                      </p>
                    </div>
                  </div>

                  <Separator />

                  {/* Pain Level */}
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Reported Pain</span>
                      <span className="font-mono font-medium">{finalExtractedData.pain_level}/10</span>
                    </div>
                    <Progress 
                      value={finalExtractedData.pain_level * 10} 
                      className="h-2.5" 
                      indicatorClassName={
                        finalExtractedData.pain_level >= 8 ? "bg-red-500" :
                        finalExtractedData.pain_level >= 5 ? "bg-orange-500" :
                        finalExtractedData.pain_level >= 3 ? "bg-yellow-500" : "bg-green-500"
                      }
                    />
                  </div>

                  <Separator />

                  {/* Symptoms */}
                  <div className="space-y-3">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Symptoms</span>
                    {finalExtractedData.symptoms.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {finalExtractedData.symptoms.map((sym, i) => (
                          <Badge key={i} variant="secondary" className="font-medium">
                            {sym}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">None identified</p>
                    )}
                  </div>

                  <Separator />

                  {/* Summary/Notes */}
                  <div className="space-y-3">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Clinical Notes</span>
                    <div className="p-4 bg-secondary/50 rounded-lg border text-sm leading-relaxed">
                      {finalExtractedData.notes || "No notes provided."}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-center space-y-4 opacity-60">
                  <Activity className="h-8 w-8 stroke-[1.5]" />
                  <p className="text-sm">No structured data extracted for this session.</p>
                </div>
              )}
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
