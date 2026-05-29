import { Badge } from "@/components/ui/badge";

type UrgencyLevel = "low" | "medium" | "high" | "critical" | "unknown";

interface UrgencyBadgeProps {
  urgency: UrgencyLevel;
  className?: string;
}

export function UrgencyBadge({ urgency, className = "" }: UrgencyBadgeProps) {
  switch (urgency) {
    case "critical":
      return <Badge variant="destructive" className={`bg-red-600 hover:bg-red-700 text-white border-transparent ${className}`}>Critical</Badge>;
    case "high":
      return <Badge variant="default" className={`bg-orange-500 hover:bg-orange-600 text-white border-transparent ${className}`}>High</Badge>;
    case "medium":
      return <Badge variant="secondary" className={`bg-yellow-500 hover:bg-yellow-600 text-white border-transparent ${className}`}>Medium</Badge>;
    case "low":
      return <Badge variant="outline" className={`bg-green-500 hover:bg-green-600 text-white border-transparent ${className}`}>Low</Badge>;
    case "unknown":
    default:
      return <Badge variant="outline" className={`bg-gray-400 hover:bg-gray-500 text-white border-transparent ${className}`}>Unknown</Badge>;
  }
}
