import { useQuery } from "@tanstack/react-query";
import { monitoringService, documentService, chatService } from "@/services";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { motion } from "framer-motion";
import {
  FileText,
  MessageSquare,
  Activity,
  Clock,
  Shield,
  TrendingUp,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";

const fallbackLatencyData = [
  { time: "00:00", retrieval: 45, reranking: 30, llm: 800 },
  { time: "04:00", retrieval: 42, reranking: 28, llm: 750 },
  { time: "08:00", retrieval: 55, reranking: 35, llm: 900 },
  { time: "12:00", retrieval: 60, reranking: 40, llm: 950 },
  { time: "16:00", retrieval: 50, reranking: 32, llm: 820 },
  { time: "20:00", retrieval: 48, reranking: 29, llm: 780 },
];

const fallbackTokenData = [
  { day: "Mon", input: 12000, output: 8000 },
  { day: "Tue", input: 15000, output: 10000 },
  { day: "Wed", input: 13000, output: 9000 },
  { day: "Thu", input: 18000, output: 12000 },
  { day: "Fri", input: 16000, output: 11000 },
  { day: "Sat", input: 8000, output: 5000 },
  { day: "Sun", input: 6000, output: 4000 },
];

function StatCard({ icon: Icon, label, value, trend }: { icon: React.ElementType; label: string; value: string | number; trend?: string }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend && <p className="text-xs text-muted-foreground mt-1">{trend}</p>}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: documents, isLoading: docsLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: documentService.list,
    retry: false,
  });
  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: chatService.listSessions,
    retry: false,
  });
  const { data: metrics } = useQuery({
    queryKey: ["metrics"],
    queryFn: monitoringService.getMetrics,
    retry: false,
    refetchInterval: 30000,
  });

  const totalDocs = documents?.length ?? 0;
  const completedDocs = documents?.filter((d) => d.status === "completed").length ?? 0;
  const totalSessions = sessions?.length ?? 0;
  const cacheHitRatio = metrics?.cache_hit_ratio ?? 0;
  const latency = metrics?.latency;

  const recentSessions = sessions?.slice(0, 5) ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Overview of your SecureRAG platform</p>
        </div>
        <Badge variant="outline" className="text-xs">
          <Activity className="mr-1 h-3 w-3" /> Live
        </Badge>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {docsLoading ? (
          <Skeleton className="h-28" />
        ) : (
          <StatCard icon={FileText} label="Documents" value={totalDocs} trend={`${completedDocs} processed`} />
        )}
        {sessionsLoading ? (
          <Skeleton className="h-28" />
        ) : (
          <StatCard icon={MessageSquare} label="Chat Sessions" value={totalSessions} />
        )}
        <StatCard
          icon={Clock}
          label="Avg Latency"
          value={latency ? (() => {
            const vals = Object.values(latency) as { average?: number }[];
            const avg = vals.reduce((sum, v) => sum + (v.average || 0), 0) / Math.max(vals.length, 1);
            return `${Math.round(avg)}ms`;
          })() : "—"}
        />
        <StatCard icon={Shield} label="Cache Hit" value={`${(cacheHitRatio * 100).toFixed(1)}%`} />
      </div>

      {/* Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Latency Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={fallbackLatencyData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis dataKey="time" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip />
                  <Area type="monotone" dataKey="retrieval" stackId="1" stroke="hsl(var(--chart-1))" fill="hsl(var(--chart-1))" fillOpacity={0.3} />
                  <Area type="monotone" dataKey="reranking" stackId="1" stroke="hsl(var(--chart-2))" fill="hsl(var(--chart-2))" fillOpacity={0.3} />
                  <Area type="monotone" dataKey="llm" stackId="1" stroke="hsl(var(--chart-3))" fill="hsl(var(--chart-3))" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Token Usage</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={fallbackTokenData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis dataKey="day" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip />
                  <Bar dataKey="input" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="output" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Recent Chats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> Recent Chats
          </CardTitle>
        </CardHeader>
        <CardContent>
          {sessionsLoading ? (
            <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}</div>
          ) : recentSessions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No chat sessions yet.</p>
          ) : (
            <div className="space-y-2">
              {recentSessions.map((s) => (
                <div key={s.id} className="flex items-center justify-between rounded-md border p-3 hover:bg-accent transition-colors">
                  <div>
                    <p className="text-sm font-medium">{s.title || "Untitled Chat"}</p>
                    <p className="text-xs text-muted-foreground">{new Date(s.created_at).toLocaleDateString()}</p>
                  </div>
                  <Badge variant="secondary" className="text-xs">Active</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
