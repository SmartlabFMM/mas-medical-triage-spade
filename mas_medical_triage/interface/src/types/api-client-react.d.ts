declare module "@workspace/api-client-react/src/generated/api.schemas" {
  export interface ExtractedData {
    is_conscious: boolean;
    pain_level: number;
    symptoms: string[];
    notes?: string;
  }
}

declare module "@workspace/api-client-react" {
  import type { ExtractedData } from "@workspace/api-client-react/src/generated/api.schemas";

  export interface TriageSession {
    id: string;
    createdAt: string;
    urgency: string;
    patientSummary?: string;
    isComplete: boolean;
  }

  export interface TriageMessage {
    id: string;
    role: "user" | "assistant";
    createdAt: string;
    content: string;
    extractedData?: ExtractedData;
  }

  export interface UseGetTriageSessionResult {
    data?: {
      session: TriageSession;
      messages: TriageMessage[];
    };
    isLoading: boolean;
    error: unknown;
  }

  export function useGetTriageSession(sessionId: string, options?: any): UseGetTriageSessionResult;
}
