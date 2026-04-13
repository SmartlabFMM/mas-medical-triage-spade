import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Activity, ShieldAlert, HeartPulse, User } from "lucide-react";
import { useCreateTriageSession, useTriageChat, getListTriageSessionsQueryKey, getGetTriageStatsQueryKey } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { UrgencyBadge } from "@/components/urgency-badge";
import { useToast } from "@/hooks/use-toast";
import type { ExtractedData } from "@workspace/api-client-react/src/generated/api.schemas";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const createSession = useCreateTriageSession();
  const chatMutation = useTriageChat();

  const initSession = async () => {
    try {
      setIsInitializing(true);
      const session = await createSession.mutateAsync();
      setSessionId(session.id);
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          content: "Hello. I am the AI Triage Nurse. Please describe your symptoms in as much detail as possible. What brings you to the emergency department today?"
        }
      ]);
    } catch (error) {
      toast({
        title: "Error starting session",
        description: "Failed to initialize triage session. Please refresh the page.",
        variant: "destructive"
      });
    } finally {
      setIsInitializing(false);
    }
  };

  useEffect(() => {
    initSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || chatMutation.isPending) return;

    const userMessage = input.trim();
    setInput("");
    
    const newUserMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userMessage
    };
    
    setMessages(prev => [...prev, newUserMsg]);

    try {
      const response = await chatMutation.mutateAsync({
        data: {
          sessionId,
          message: userMessage
        }
      });

      const newAssistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.reply
      };

      setMessages(prev => [...prev, newAssistantMsg]);
      
      if (response.extracted_data) {
        setExtractedData(response.extracted_data);
      }

      if (response.is_complete) {
        queryClient.invalidateQueries({ queryKey: getListTriageSessionsQueryKey() });
        queryClient.invalidateQueries({ queryKey: getGetTriageStatsQueryKey() });
        toast({
          title: "Triage Complete",
          description: "Your session has been logged and sent to the clinical team."
        });
      }

    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send message. Please try again.",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="flex-1 flex flex-col md:flex-row h-full overflow-hidden bg-background">
      
      {/* Chat Section */}
      <div className="flex-1 flex flex-col border-r h-full relative">
        <div className="h-14 border-b bg-card flex items-center px-6 shrink-0 shadow-sm z-10">
          <h2 className="font-semibold flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Triage Terminal
          </h2>
          {isInitializing && <span className="ml-4 text-xs text-muted-foreground animate-pulse">Initializing Secure Connection...</span>}
        </div>

        <div className="flex-1 overflow-y-auto p-4 md:p-6 bg-slate-50/50 dark:bg-slate-900/20">
          <div className="max-w-3xl mx-auto flex flex-col gap-6">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <Activity className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  
                  <div 
                    className={`px-4 py-3 rounded-lg max-w-[80%] shadow-sm ${
                      msg.role === "user" 
                        ? "bg-primary text-primary-foreground rounded-tr-sm" 
                        : "bg-card border rounded-tl-sm text-foreground"
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{msg.content}</p>
                  </div>

                  {msg.role === "user" && (
                    <div className="h-8 w-8 rounded-full bg-secondary border flex items-center justify-center shrink-0">
                      <User className="h-4 w-4 text-muted-foreground" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            
            {chatMutation.isPending && (
              <motion.div 
                initial={{ opacity: 0 }} 
                animate={{ opacity: 1 }} 
                className="flex gap-4 justify-start"
              >
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                  <Activity className="h-4 w-4 text-primary" />
                </div>
                <div className="px-4 py-3 rounded-lg bg-card border rounded-tl-sm shadow-sm flex items-center gap-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-primary/40 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                    <div className="w-2 h-2 bg-primary/40 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                    <div className="w-2 h-2 bg-primary/40 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                  </div>
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>

        <div className="p-4 bg-card border-t shrink-0">
          <form onSubmit={handleSend} className="max-w-3xl mx-auto relative flex items-center">
            <Input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe your symptoms..."
              disabled={isInitializing || chatMutation.isPending || !sessionId}
              className="pr-12 h-12 text-base shadow-sm focus-visible:ring-primary"
            />
            <Button 
              type="submit" 
              size="icon"
              disabled={!input.trim() || isInitializing || chatMutation.isPending || !sessionId}
              className="absolute right-1 h-10 w-10 transition-transform active:scale-95"
            >
              <Send className="h-4 w-4" />
              <span className="sr-only">Send</span>
            </Button>
          </form>
        </div>
      </div>

      {/* Extracted Data Panel */}
      <div className="w-full md:w-80 bg-card shrink-0 flex flex-col border-t md:border-t-0 shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.03)] z-20">
        <div className="h-14 border-b flex items-center px-4 shrink-0 bg-slate-50/50 dark:bg-slate-900/50">
          <h3 className="font-semibold text-sm flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-muted-foreground" />
            Live Clinical Extraction
          </h3>
        </div>
        
        <div className="p-4 flex-1 overflow-y-auto">
          {!extractedData ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground p-6 text-center space-y-4 opacity-60">
              <Activity className="h-8 w-8 stroke-[1.5]" />
              <p className="text-sm">Awaiting clinical input to begin data extraction.</p>
            </div>
          ) : (
            <AnimatePresence mode="wait">
              <motion.div 
                key={JSON.stringify(extractedData)}
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-6"
              >
                {/* Urgency */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Assessed Urgency</span>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {(extractedData.confidence * 100).toFixed(0)}% CONFIDENCE
                    </Badge>
                  </div>
                  <div className="p-3 border rounded-lg bg-slate-50/50 dark:bg-slate-900/50 flex items-center justify-center">
                    <UrgencyBadge urgency={extractedData.urgency} className="text-sm px-4 py-1" />
                  </div>
                </div>

                <Separator />

                {/* Symptoms */}
                <div className="space-y-2">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Identified Symptoms</span>
                  {extractedData.symptoms.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {extractedData.symptoms.map((sym, i) => (
                        <Badge key={i} variant="secondary" className="font-medium bg-secondary text-secondary-foreground border border-border/50">
                          {sym}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">None identified yet</p>
                  )}
                </div>

                <Separator />

                {/* Pain Scale */}
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                      <HeartPulse className="h-3 w-3" /> Pain Level
                    </span>
                    <span className="font-mono font-medium text-sm">{extractedData.pain_level}/10</span>
                  </div>
                  <Progress 
                    value={extractedData.pain_level * 10} 
                    className="h-2.5" 
                    indicatorClassName={
                      extractedData.pain_level >= 8 ? "bg-red-500" :
                      extractedData.pain_level >= 5 ? "bg-orange-500" :
                      extractedData.pain_level >= 3 ? "bg-yellow-500" : "bg-green-500"
                    }
                  />
                  <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                    <span>0 (NONE)</span>
                    <span>10 (SEVERE)</span>
                  </div>
                </div>

                <Separator />

                {/* Status */}
                <div className="space-y-2">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Vitals & Status</span>
                  <div className="grid grid-cols-2 gap-2">
                    <Card className="shadow-none bg-slate-50/50 dark:bg-slate-900/50 border-border/60">
                      <CardContent className="p-3 flex flex-col items-center justify-center text-center space-y-1">
                        <span className="text-[10px] text-muted-foreground uppercase">Conscious</span>
                        <span className={`text-sm font-semibold ${extractedData.is_conscious ? "text-green-600 dark:text-green-500" : "text-red-600 dark:text-red-500"}`}>
                          {extractedData.is_conscious ? "YES" : "NO"}
                        </span>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                {extractedData.notes && (
                  <div className="space-y-2 pt-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Clinical Notes</span>
                    <p className="text-sm p-3 bg-secondary/50 rounded-lg border border-border/50 text-secondary-foreground leading-relaxed">
                      {extractedData.notes}
                    </p>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          )}
        </div>
      </div>
    </div>
  );
}
