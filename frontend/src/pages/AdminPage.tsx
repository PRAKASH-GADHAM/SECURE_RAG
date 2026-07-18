import { useState, useMemo, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  monitoringService,
  adminService,
  securityService,
  healthService,
  guardrailsService,
} from "@/services";
import type {
  MetricsData,
  SecurityEvent,
  AdminStats,
  UserAdmin,
  AdminAuditLog,
  HealthResponse,
  SystemConfig,
  BenchmarkResult,
  EvaluationResult,
  PaginatedResponse,
  LatencyMetrics,
} from "@/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import {
  Users,
  Shield,
  Database,
  Brain,
  BarChart3,
  Activity,
  Settings,
  FileText,
  RefreshCw,
  Loader2,
  Search,
  Trash2,
  AlertTriangle,
  CheckCircle,
  Server,
  Cpu,
  HardDrive,
  Zap,
  Lock,
  Filter,
  ChevronLeft,
  ChevronRight,
  Clock,
  LayoutDashboard,
  MessageSquare,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const chartColors = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

const fallbackLatencyData: { hour: string; p50: number; p95: number; p99: number }[] = [
  { hour: "00:00", p50: 45, p95: 120, p99: 300 },
  { hour: "04:00", p50: 42, p95: 110, p99: 280 },
  { hour: "08:00", p50: 55, p95: 140, p99: 350 },
  { hour: "12:00", p50: 60, p95: 150, p99: 380 },
  { hour: "16:00", p50: 50, p95: 130, p99: 320 },
  { hour: "20:00", p50: 48, p95: 125, p99: 310 },
];

const fallbackSecurityData = [
  { name: "Injection", count: 12 },
  { name: "Jailbreak", count: 5 },
  { name: "PII Leak", count: 8 },
  { name: "Moderation", count: 3 },
];

const fallbackEvaluation: EvaluationResult = {
  retrieval: { precision_5: 0.72, recall_5: 0.85, mrr: 0.68, ndcg_5: 0.79 },
  reranking: { ndcg_10: 0.82, mrr: 0.75 },
  hallucination: { groundedness: 0.88, context_overlap: 0.76 },
  citation: { accuracy: 0.91 },
  overall_score: 0.81,
};

const fallbackConfig: SystemConfig = {
  llm_provider: "openai",
  llm_model: "gpt-4",
  embedding_model: "text-embedding-3-small",
  vector_db: "pgvector",
  chunk_size: 512,
  chunk_overlap: 50,
  max_top_k: 10,
  enable_reranking: true,
  enable_guardrails: true,
  cache_ttl_seconds: 3600,
  rate_limit_per_minute: 60,
};

const fallbackBenchmarks: Record<string, BenchmarkResult> = {
  query: { iterations: 100, total_time_ms: 12500, average_time_ms: 125, min_time_ms: 45, max_time_ms: 890, p50_ms: 110, p95_ms: 320, p99_ms: 780, success_rate: 0.98, error_count: 2 },
  retrieval: { iterations: 100, total_time_ms: 4200, average_time_ms: 42, min_time_ms: 12, max_time_ms: 210, p50_ms: 35, p95_ms: 85, p99_ms: 180, success_rate: 0.99, error_count: 1 },
  embedding: { iterations: 100, total_time_ms: 6800, average_time_ms: 68, min_time_ms: 22, max_time_ms: 340, p50_ms: 58, p95_ms: 150, p99_ms: 290, success_rate: 1.0, error_count: 0 },
};

const severityColorMap: Record<string, string> = {
  low: "text-blue-600 bg-blue-50 dark:bg-blue-950 dark:text-blue-400",
  medium: "text-yellow-600 bg-yellow-50 dark:bg-yellow-950 dark:text-yellow-400",
  high: "text-orange-600 bg-orange-50 dark:bg-orange-950 dark:text-orange-400",
  critical: "text-red-600 bg-red-50 dark:bg-red-950 dark:text-red-400",
};

const severityBadgeVariant: Record<string, "default" | "secondary" | "destructive" | "success" | "warning" | "outline"> = {
  low: "secondary",
  medium: "warning",
  high: "warning",
  critical: "destructive",
};

const fadeIn = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.25 } },
};

function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-3 w-24" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-7 w-16" />
      </CardContent>
    </Card>
  );
}

function ChartSkeleton({ height = 280 }: { height?: number }) {
  return <Skeleton className={`w-full h-[${height}px]`} />;
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hrs = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${days}d ${hrs}h ${mins}m`;
}

function serviceIcon(name: string) {
  switch (name.toLowerCase()) {
    case "redis": return <HardDrive className="h-5 w-5" />;
    case "postgresql": return <Database className="h-5 w-5" />;
    case "celery": return <Cpu className="h-5 w-5" />;
    default: return <Server className="h-5 w-5" />;
  }
}

export default function AdminPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("overview");
  const [securityFilter, setSecurityFilter] = useState<string>("all");
  const [auditPage, setAuditPage] = useState(1);
  const [auditSeverity, setAuditSeverity] = useState<string>("all");
  const [auditSearch, setAuditSearch] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [deleteDialogUser, setDeleteDialogUser] = useState<UserAdmin | null>(null);
  const [guardrailsInput, setGuardrailsInput] = useState("");
  const [guardrailsResult, setGuardrailsResult] = useState<{ safe: boolean; categories: Record<string, number>; flagged: string[] } | null>(null);
  const [configForm, setConfigForm] = useState<Partial<SystemConfig>>({});

  const { data: metrics, isLoading: metricsLoading } = useQuery<MetricsData>({
    queryKey: ["admin-metrics"],
    queryFn: monitoringService.getMetrics,
    retry: false,
    refetchInterval: 30000,
  });

  const { data: stats, isLoading: statsLoading } = useQuery<AdminStats>({
    queryKey: ["admin-stats"],
    queryFn: adminService.getStats,
    retry: false,
  });

  const { data: benchmarks, isLoading: benchmarksLoading } = useQuery<Record<string, BenchmarkResult>>({
    queryKey: ["admin-benchmarks"],
    queryFn: monitoringService.getBenchmarks,
    retry: false,
  });

  const { data: securityEvents, isLoading: securityLoading } = useQuery<SecurityEvent[]>({
    queryKey: ["security-events"],
    queryFn: securityService.getAuditLogs,
    retry: false,
  });

  const { data: securityStats } = useQuery<Record<string, unknown>>({
    queryKey: ["security-stats"],
    queryFn: securityService.getStatistics,
    retry: false,
  });

  const { data: latencyData, isLoading: latencyLoading } = useQuery<Record<string, unknown>>({
    queryKey: ["latency-metrics"],
    queryFn: monitoringService.getLatencyMetrics,
    retry: false,
    refetchInterval: 30000,
  });

  const { data: users, isLoading: usersLoading } = useQuery<UserAdmin[]>({
    queryKey: ["admin-users"],
    queryFn: adminService.listUsers,
    retry: false,
  });

  const { data: auditLogs, isLoading: auditLogsLoading } = useQuery<PaginatedResponse<AdminAuditLog>>({
    queryKey: ["admin-audit-logs", auditPage, auditSeverity],
    queryFn: () => adminService.getAuditLogs({
      page: auditPage,
      page_size: 10,
      severity: auditSeverity === "all" ? undefined : auditSeverity,
    }),
    retry: false,
  });

  const { data: health, isLoading: healthLoading } = useQuery<HealthResponse>({
    queryKey: ["admin-health"],
    queryFn: healthService.getDetailedHealth,
    retry: false,
    refetchInterval: 15000,
  });

  const { data: systemConfig, isLoading: configLoading } = useQuery<SystemConfig>({
    queryKey: ["admin-config"],
    queryFn: adminService.getSystemConfig,
    retry: false,
  });

  const { data: guardrailsStats } = useQuery<Record<string, unknown>>({
    queryKey: ["guardrails-stats"],
    queryFn: guardrailsService.getStatistics,
    retry: false,
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) => adminService.updateUserRole(id, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      toast({ title: "Role updated", description: "User role has been changed." });
    },
    onError: () => toast({ title: "Failed", description: "Could not update role.", variant: "destructive" }),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => adminService.toggleUserActive(id, active),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      toast({ title: "User updated", description: "Active status toggled." });
    },
    onError: () => toast({ title: "Failed", description: "Could not update user.", variant: "destructive" }),
  });

  const deleteUserMutation = useMutation({
    mutationFn: (id: string) => adminService.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setDeleteDialogUser(null);
      toast({ title: "User deleted", description: "User has been removed." });
    },
    onError: () => toast({ title: "Failed", description: "Could not delete user.", variant: "destructive" }),
  });

  const updateConfigMutation = useMutation({
    mutationFn: (cfg: Partial<SystemConfig>) => adminService.updateSystemConfig(cfg),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-config"] });
      toast({ title: "Config saved", description: "System configuration updated." });
    },
    onError: () => toast({ title: "Failed", description: "Could not save config.", variant: "destructive" }),
  });

  const guardrailsCheckMutation = useMutation({
    mutationFn: (text: string) => guardrailsService.checkContent(text),
    onSuccess: (data) => {
      setGuardrailsResult(data);
    },
    onError: () => toast({ title: "Failed", description: "Guardrails check failed.", variant: "destructive" }),
  });

  const filteredSecurityEvents = useMemo(() => {
    if (!securityEvents) return [];
    if (securityFilter === "all") return securityEvents;
    return securityEvents.filter((e) => e.severity === securityFilter);
  }, [securityEvents, securityFilter]);

  const filteredUsers = useMemo(() => {
    if (!users) return [];
    if (!userSearch) return users;
    const q = userSearch.toLowerCase();
    return users.filter(
      (u) =>
        u.email.toLowerCase().includes(q) ||
        u.username.toLowerCase().includes(q) ||
        (u.full_name && u.full_name.toLowerCase().includes(q)),
    );
  }, [users, userSearch]);

  const filteredAuditLogs = useMemo(() => {
    if (!auditLogs?.items) return [];
    if (!auditSearch) return auditLogs.items;
    const q = auditSearch.toLowerCase();
    return auditLogs.items.filter(
      (l) => l.description.toLowerCase().includes(q) || l.event_type.toLowerCase().includes(q),
    );
  }, [auditLogs, auditSearch]);

  const latencyChartData = useMemo(() => {
    if (latencyData && typeof latencyData === "object" && !Array.isArray(latencyData)) {
      const entries = Object.entries(latencyData);
      if (entries.length > 0) {
        return entries.map(([service, val]) => ({
          service,
          p50: (val as LatencyMetrics).p50 ?? 0,
          p95: (val as LatencyMetrics).p95 ?? 0,
          p99: (val as LatencyMetrics).p99 ?? 0,
          avg: (val as LatencyMetrics).average ?? 0,
        }));
      }
    }
    return fallbackLatencyData.map((d) => ({
      service: d.hour,
      p50: d.p50,
      p95: d.p95,
      p99: d.p99,
      avg: Math.round((d.p50 + d.p95) / 2),
    }));
  }, [latencyData]);

  const benchmarkData = benchmarks ?? fallbackBenchmarks;
  const evalData: EvaluationResult = fallbackEvaluation;
  const activeConfig = systemConfig ?? fallbackConfig;

  const effectiveConfig = useMemo(() => ({ ...activeConfig, ...configForm }), [activeConfig, configForm]);

  const handleConfigChange = useCallback((key: keyof SystemConfig, value: string | number | boolean) => {
    setConfigForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  const securityChartData = useMemo(() => {
    if (securityEvents && securityEvents.length > 0) {
      const counts: Record<string, number> = {};
      securityEvents.forEach((e) => {
        counts[e.severity] = (counts[e.severity] || 0) + 1;
      });
      return Object.entries(counts).map(([name, count]) => ({ name, count }));
    }
    return fallbackSecurityData;
  }, [securityEvents]);

  const guardrailsChartData = useMemo(() => {
    if (guardrailsStats && typeof guardrailsStats === "object") {
      return Object.entries(guardrailsStats).map(([name, value]) => ({
        name: String(name),
        count: typeof value === "number" ? value : 0,
      }));
    }
    return [
      { name: "Blocked", count: 24 },
      { name: "Allowed", count: 1847 },
      { name: "Flagged", count: 15 },
    ];
  }, [guardrailsStats]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Admin Portal</h1>
          <p className="text-muted-foreground">System management and monitoring</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => queryClient.invalidateQueries()}
          className="gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh All
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="flex-wrap h-auto gap-1 p-1">
          <TabsTrigger value="overview" className="gap-2"><LayoutDashboard className="h-4 w-4" />Overview</TabsTrigger>
          <TabsTrigger value="metrics" className="gap-2"><BarChart3 className="h-4 w-4" />Metrics</TabsTrigger>
          <TabsTrigger value="latency" className="gap-2"><Activity className="h-4 w-4" />Latency</TabsTrigger>
          <TabsTrigger value="security" className="gap-2"><Shield className="h-4 w-4" />Security</TabsTrigger>
          <TabsTrigger value="users" className="gap-2"><Users className="h-4 w-4" />Users</TabsTrigger>
          <TabsTrigger value="audit" className="gap-2"><FileText className="h-4 w-4" />Audit Logs</TabsTrigger>
          <TabsTrigger value="evaluation" className="gap-2"><Brain className="h-4 w-4" />Evaluation</TabsTrigger>
          <TabsTrigger value="infrastructure" className="gap-2"><Database className="h-4 w-4" />Infrastructure</TabsTrigger>
          <TabsTrigger value="guardrails" className="gap-2"><Lock className="h-4 w-4" />Guardrails</TabsTrigger>
          <TabsTrigger value="config" className="gap-2"><Settings className="h-4 w-4" />Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
              {statsLoading ? (
                Array.from({ length: 5 }).map((_, i) => <StatCardSkeleton key={i} />)
              ) : (
                <>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Users className="h-3 w-3" />Total Users</CardTitle>
                    </CardHeader>
                    <CardContent><p className="text-2xl font-bold">{stats?.total_users ?? 0}</p></CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><CheckCircle className="h-3 w-3" />Active Users</CardTitle>
                    </CardHeader>
                    <CardContent><p className="text-2xl font-bold text-green-600">{stats?.active_users ?? 0}</p></CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><FileText className="h-3 w-3" />Documents</CardTitle>
                    </CardHeader>
                    <CardContent><p className="text-2xl font-bold">{stats?.total_documents ?? 0}</p></CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><MessageSquare className="h-3 w-3" />Total Chats</CardTitle>
                    </CardHeader>
                    <CardContent><p className="text-2xl font-bold">{stats?.total_chats ?? 0}</p></CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Activity className="h-3 w-3" />System Health</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {healthLoading ? (
                        <Skeleton className="h-6 w-20" />
                      ) : (
                        <Badge variant={health?.status === "healthy" ? "success" : health?.status === "degraded" ? "warning" : "destructive"}>
                          {health?.status ?? "Unknown"}
                        </Badge>
                      )}
                    </CardContent>
                  </Card>
                </>
              )}
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Request Activity</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={[
                      { time: "1m", requests: metrics?.counters?.requests_1m ?? 42, errors: metrics?.counters?.errors_1m ?? 2 },
                      { time: "5m", requests: metrics?.counters?.requests_5m ?? 180, errors: metrics?.counters?.errors_5m ?? 8 },
                      { time: "15m", requests: metrics?.counters?.requests_15m ?? 520, errors: metrics?.counters?.errors_15m ?? 15 },
                      { time: "30m", requests: metrics?.counters?.requests_30m ?? 980, errors: metrics?.counters?.errors_30m ?? 25 },
                      { time: "1h", requests: metrics?.counters?.requests_1h ?? 1840, errors: metrics?.counters?.errors_1h ?? 40 },
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis dataKey="time" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip />
                      <Area type="monotone" dataKey="requests" stroke={chartColors[0]} fill={chartColors[0]} fillOpacity={0.2} strokeWidth={2} />
                      <Area type="monotone" dataKey="errors" stroke="hsl(var(--destructive))" fill="hsl(var(--destructive))" fillOpacity={0.1} strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Security Event Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={securityChartData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis dataKey="name" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {securityChartData.map((_, i) => (
                          <Cell key={i} fill={chartColors[i % chartColors.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        </TabsContent>

        <TabsContent value="metrics">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {metricsLoading ? (
                Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)
              ) : (
                <>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground">Cache Hit Ratio</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">{((metrics?.cache_hit_ratio ?? 0.75) * 100).toFixed(1)}%</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground">Total Requests</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">{metrics?.counters?.requests ?? 4280}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground">Errors</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold text-destructive">{metrics?.counters?.errors ?? 23}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground">Active Users</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">{stats?.active_users ?? 12}</p>
                    </CardContent>
                  </Card>
                </>
              )}
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Latency Distribution</CardTitle>
                  <CardDescription>p50, p95, p99 over time</CardDescription>
                </CardHeader>
                <CardContent>
                  {metricsLoading ? <ChartSkeleton /> : (
                    <ResponsiveContainer width="100%" height={280}>
                      <LineChart data={fallbackLatencyData}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                        <XAxis dataKey="hour" className="text-xs" />
                        <YAxis className="text-xs" />
                        <Tooltip />
                        <Line type="monotone" dataKey="p50" stroke={chartColors[0]} strokeWidth={2} dot={false} name="p50" />
                        <Line type="monotone" dataKey="p95" stroke={chartColors[1]} strokeWidth={2} dot={false} name="p95" />
                        <Line type="monotone" dataKey="p99" stroke={chartColors[2]} strokeWidth={2} dot={false} name="p99" />
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Token Usage</CardTitle>
                  <CardDescription>Estimated token consumption</CardDescription>
                </CardHeader>
                <CardContent>
                  {metricsLoading ? <ChartSkeleton /> : (
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={[
                        { hour: "00", tokens: 1200 },
                        { hour: "04", tokens: 800 },
                        { hour: "08", tokens: 3400 },
                        { hour: "12", tokens: 4200 },
                        { hour: "16", tokens: 3800 },
                        { hour: "20", tokens: 2600 },
                      ]}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                        <XAxis dataKey="hour" className="text-xs" />
                        <YAxis className="text-xs" />
                        <Tooltip />
                        <Bar dataKey="tokens" fill={chartColors[3]} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </CardContent>
              </Card>
            </div>
          </motion.div>
        </TabsContent>

        <TabsContent value="latency">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            {latencyLoading ? (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {latencyChartData.slice(0, 4).map((item) => (
                  <Card key={item.service}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs text-muted-foreground capitalize">{item.service}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-1">
                      <div className="flex justify-between text-xs"><span className="text-muted-foreground">p50</span><span className="font-mono">{item.p50}ms</span></div>
                      <div className="flex justify-between text-xs"><span className="text-muted-foreground">p95</span><span className="font-mono">{item.p95}ms</span></div>
                      <div className="flex justify-between text-xs"><span className="text-muted-foreground">p99</span><span className="font-mono">{item.p99}ms</span></div>
                      <div className="flex justify-between text-xs"><span className="text-muted-foreground">avg</span><span className="font-mono">{item.avg}ms</span></div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Latency Over Time by Service</CardTitle>
                <CardDescription>p50, p95, p99 latency for each component</CardDescription>
              </CardHeader>
              <CardContent>
                {latencyLoading ? <ChartSkeleton height={350} /> : (
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={latencyChartData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis dataKey="service" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip formatter={(v: number) => `${v}ms`} />
                      <Line type="monotone" dataKey="p50" stroke={chartColors[0]} strokeWidth={2} dot={{ r: 3 }} name="p50" />
                      <Line type="monotone" dataKey="p95" stroke={chartColors[1]} strokeWidth={2} dot={{ r: 3 }} name="p95" />
                      <Line type="monotone" dataKey="p99" stroke={chartColors[2]} strokeWidth={2} dot={{ r: 3 }} name="p99" />
                      <Line type="monotone" dataKey="avg" stroke={chartColors[3]} strokeWidth={1} strokeDasharray="5 5" dot={false} name="avg" />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="security">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Security Events</h2>
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <Select value={securityFilter} onValueChange={setSecurityFilter}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Severities</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground">Total Events</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">{Number((securityStats as Record<string, unknown>)?.total_events) || securityEvents?.length || 0}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground">Critical Events</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-destructive">
                    {securityEvents?.filter((e) => e.severity === "critical").length ?? 0}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground">Blocked Threats</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">
                    {Number((securityStats as Record<string, unknown>)?.blocked) || securityEvents?.filter((e) => e.severity === "critical" || e.severity === "high").length || 0}
                  </p>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Security Events by Severity</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={securityChartData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="name" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {securityChartData.map((entry, i) => (
                        <Cell
                          key={i}
                          fill={
                            entry.name === "critical" ? "hsl(var(--destructive))"
                            : entry.name === "high" ? "hsl(24, 95%, 53%)"
                            : entry.name === "medium" ? "hsl(45, 93%, 47%)"
                            : chartColors[i % chartColors.length]
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Event Feed</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  {securityLoading ? (
                    <div className="space-y-2">
                      {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {filteredSecurityEvents.map((event) => (
                        <div key={event.id} className="flex items-center justify-between rounded-md border p-3">
                          <div className="flex items-center gap-3">
                            <Shield className="h-4 w-4 text-destructive" />
                            <div>
                              <p className="text-sm">{event.description}</p>
                              <p className="text-xs text-muted-foreground">{event.event_type} &middot; {new Date(event.created_at).toLocaleString()}</p>
                            </div>
                          </div>
                          <Badge variant={severityBadgeVariant[event.severity]} className={severityColorMap[event.severity]}>
                            {event.severity}
                          </Badge>
                        </div>
                      ))}
                      {filteredSecurityEvents.length === 0 && (
                        <p className="text-sm text-muted-foreground text-center py-8">No events found.</p>
                      )}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="users">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">User Management</h2>
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search users..."
                  value={userSearch}
                  onChange={(e) => { setUserSearch(e.target.value); }}
                  className="pl-9"
                />
              </div>
            </div>

            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-4 font-medium text-muted-foreground">User</th>
                        <th className="text-left p-4 font-medium text-muted-foreground">Email</th>
                        <th className="text-left p-4 font-medium text-muted-foreground">Role</th>
                        <th className="text-left p-4 font-medium text-muted-foreground">Status</th>
                        <th className="text-left p-4 font-medium text-muted-foreground">Last Login</th>
                        <th className="text-right p-4 font-medium text-muted-foreground">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usersLoading ? (
                        Array.from({ length: 5 }).map((_, i) => (
                          <tr key={i} className="border-b">
                            <td colSpan={6} className="p-4"><Skeleton className="h-8 w-full" /></td>
                          </tr>
                        ))
                      ) : (
                        filteredUsers.map((user) => (
                          <tr key={user.id} className="border-b last:border-0 hover:bg-muted/50">
                            <td className="p-4">
                              <div>
                                <p className="font-medium">{user.full_name ?? user.username}</p>
                                <p className="text-xs text-muted-foreground">@{user.username}</p>
                              </div>
                            </td>
                            <td className="p-4 text-muted-foreground">{user.email}</td>
                            <td className="p-4">
                              <Select
                                value={user.role}
                                onValueChange={(role) => updateRoleMutation.mutate({ id: user.id, role })}
                              >
                                <SelectTrigger className="w-[100px] h-8">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="admin">Admin</SelectItem>
                                  <SelectItem value="user">User</SelectItem>
                                </SelectContent>
                              </Select>
                            </td>
                            <td className="p-4">
                              <div className="flex items-center gap-2">
                                <Badge variant={user.is_active ? "success" : "secondary"}>
                                  {user.is_active ? "Active" : "Inactive"}
                                </Badge>
                              </div>
                            </td>
                            <td className="p-4 text-xs text-muted-foreground">
                              {user.last_login ? new Date(user.last_login).toLocaleDateString() : "Never"}
                            </td>
                            <td className="p-4">
                              <div className="flex items-center justify-end gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0"
                                  onClick={() => toggleActiveMutation.mutate({ id: user.id, active: !user.is_active })}
                                >
                                  {user.is_active ? (
                                    <ToggleRight className="h-4 w-4 text-green-600" />
                                  ) : (
                                    <ToggleLeft className="h-4 w-4 text-muted-foreground" />
                                  )}
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                                  onClick={() => setDeleteDialogUser(user)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="audit">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Audit Logs</h2>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search logs..."
                    value={auditSearch}
                    onChange={(e) => setAuditSearch(e.target.value)}
                    className="pl-9 w-[200px]"
                  />
                </div>
                <Select value={auditSeverity} onValueChange={(v) => { setAuditSeverity(v); setAuditPage(1); }}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Severities</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-4 font-medium text-muted-foreground">Timestamp</th>
                        <th className="text-left p-4 font-medium text-muted-foreground">Event</th>
                        <th className="text-left p-4 font-medium text-muted-foreground">Description</th>
                        <th className="text-left p-4 font-medium text-muted-foreground">User</th>
                        <th className="text-left p-4 font-medium text-muted-foreground">Severity</th>
                        <th className="text-left p-4 font-medium text-muted-foreground">IP</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogsLoading ? (
                        Array.from({ length: 8 }).map((_, i) => (
                          <tr key={i} className="border-b">
                            <td colSpan={6} className="p-4"><Skeleton className="h-6 w-full" /></td>
                          </tr>
                        ))
                      ) : (
                        filteredAuditLogs.map((log) => (
                          <tr key={log.id} className="border-b last:border-0 hover:bg-muted/50">
                            <td className="p-4 text-xs text-muted-foreground whitespace-nowrap">
                              {new Date(log.created_at).toLocaleString()}
                            </td>
                            <td className="p-4">
                              <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{log.event_type}</span>
                            </td>
                            <td className="p-4 max-w-xs truncate">{log.description}</td>
                            <td className="p-4 text-xs text-muted-foreground">{log.username ?? log.user_id}</td>
                            <td className="p-4">
                              <Badge variant={severityBadgeVariant[log.severity]} className={severityColorMap[log.severity]}>
                                {log.severity}
                              </Badge>
                            </td>
                            <td className="p-4 text-xs text-muted-foreground font-mono">{log.ip_address}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            {auditLogs && auditLogs.total_pages > 1 && (
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Page {auditLogs.page} of {auditLogs.total_pages} ({auditLogs.total} total)
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={auditPage <= 1}
                    onClick={() => setAuditPage((p) => p - 1)}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={auditPage >= auditLogs.total_pages}
                    onClick={() => setAuditPage((p) => p + 1)}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        </TabsContent>

        <TabsContent value="evaluation">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Retrieval Quality</CardTitle>
                  <CardDescription>Precision, Recall, MRR, nDCG metrics</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {[
                    ["Precision@5", evalData.retrieval.precision_5],
                    ["Recall@5", evalData.retrieval.recall_5],
                    ["MRR", evalData.retrieval.mrr],
                    ["nDCG@5", evalData.retrieval.ndcg_5],
                  ].map(([label, value]) => (
                    <div key={String(label)}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-muted-foreground">{String(label)}</span>
                        <span className="text-sm font-mono font-medium">{typeof value === "number" ? value.toFixed(2) : value}</span>
                      </div>
                      {typeof value === "number" && (
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-primary rounded-full" style={{ width: `${value * 100}%` }} />
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Hallucination Metrics</CardTitle>
                  <CardDescription>Groundedness and context overlap</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {[
                    ["Groundedness", evalData.hallucination.groundedness],
                    ["Context Overlap", evalData.hallucination.context_overlap],
                    ["Citation Accuracy", evalData.citation.accuracy],
                    ["Overall Score", evalData.overall_score],
                  ].map(([label, value]) => (
                    <div key={String(label)}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-muted-foreground">{String(label)}</span>
                        <span className="text-sm font-mono font-medium">{typeof value === "number" ? value.toFixed(2) : value}</span>
                      </div>
                      {typeof value === "number" && (
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${value >= 0.8 ? "bg-green-500" : value >= 0.6 ? "bg-yellow-500" : "bg-red-500"}`}
                            style={{ width: `${value * 100}%` }}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Benchmark Results</CardTitle>
                <CardDescription>Performance benchmarks for key services</CardDescription>
              </CardHeader>
              <CardContent>
                {benchmarksLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left p-3 font-medium text-muted-foreground">Service</th>
                          <th className="text-right p-3 font-medium text-muted-foreground">Iterations</th>
                          <th className="text-right p-3 font-medium text-muted-foreground">Avg (ms)</th>
                          <th className="text-right p-3 font-medium text-muted-foreground">p50 (ms)</th>
                          <th className="text-right p-3 font-medium text-muted-foreground">p95 (ms)</th>
                          <th className="text-right p-3 font-medium text-muted-foreground">p99 (ms)</th>
                          <th className="text-right p-3 font-medium text-muted-foreground">Success</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(benchmarkData).map(([name, result]) => (
                          <tr key={name} className="border-b last:border-0 hover:bg-muted/50">
                            <td className="p-3 font-medium capitalize">{name}</td>
                            <td className="p-3 text-right font-mono">{result.iterations}</td>
                            <td className="p-3 text-right font-mono">{result.average_time_ms}</td>
                            <td className="p-3 text-right font-mono">{result.p50_ms}</td>
                            <td className="p-3 text-right font-mono">{result.p95_ms}</td>
                            <td className="p-3 text-right font-mono">{result.p99_ms}</td>
                            <td className="p-3 text-right">
                              <Badge variant={result.success_rate >= 0.99 ? "success" : result.success_rate >= 0.95 ? "warning" : "destructive"}>
                                {(result.success_rate * 100).toFixed(1)}%
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="infrastructure">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Activity className="h-3 w-3" />Status</CardTitle>
                </CardHeader>
                <CardContent>
                  {healthLoading ? <Skeleton className="h-6 w-20" /> : (
                    <Badge variant={health?.status === "healthy" ? "success" : health?.status === "degraded" ? "warning" : "destructive"}>
                      {health?.status ?? "Unknown"}
                    </Badge>
                  )}
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Zap className="h-3 w-3" />Version</CardTitle>
                </CardHeader>
                <CardContent><p className="text-lg font-bold">{health?.version ?? "N/A"}</p></CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Clock className="h-3 w-3" />Uptime</CardTitle>
                </CardHeader>
                <CardContent><p className="text-lg font-bold">{health ? formatUptime(health.uptime_seconds) : "N/A"}</p></CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Server className="h-3 w-3" />Services</CardTitle>
                </CardHeader>
                <CardContent><p className="text-lg font-bold">{health?.services ? Object.keys(health.services).length : 0}</p></CardContent>
              </Card>
            </div>

            <h3 className="text-sm font-semibold">Service Status</h3>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {healthLoading ? (
                Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32" />)
              ) : health?.services ? (
                Object.entries(health.services).map(([name, svc]) => (
                  <Card key={name}>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {serviceIcon(name)}
                          <CardTitle className="text-sm">{name}</CardTitle>
                        </div>
                        <Badge variant={svc.status === "healthy" ? "success" : svc.status === "degraded" ? "warning" : "destructive"}>
                          {svc.status}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {svc.latency_ms !== undefined && (
                        <p className="text-xs text-muted-foreground">Latency: <span className="font-mono">{svc.latency_ms}ms</span></p>
                      )}
                    </CardContent>
                  </Card>
                ))
              ) : (
                <>
                  <Card>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2"><HardDrive className="h-5 w-5" /><CardTitle className="text-sm">Redis</CardTitle></div>
                        <Badge variant="success">healthy</Badge>
                      </div>
                    </CardHeader>
                    <CardContent><p className="text-xs text-muted-foreground">Connected</p></CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2"><Database className="h-5 w-5" /><CardTitle className="text-sm">PostgreSQL</CardTitle></div>
                        <Badge variant="success">healthy</Badge>
                      </div>
                    </CardHeader>
                    <CardContent><p className="text-xs text-muted-foreground">Connected</p></CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2"><Cpu className="h-5 w-5" /><CardTitle className="text-sm">Celery Workers</CardTitle></div>
                        <Badge variant="success">healthy</Badge>
                      </div>
                    </CardHeader>
                    <CardContent><p className="text-xs text-muted-foreground">2 active</p></CardContent>
                  </Card>
                </>
              )}
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Current System Configuration</CardTitle>
                <CardDescription>Read-only snapshot of active config</CardDescription>
              </CardHeader>
              <CardContent>
                {configLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-6 w-full" />)}
                  </div>
                ) : (
                  <div className="grid gap-2 md:grid-cols-2">
                    {Object.entries(activeConfig).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between rounded border p-2">
                        <span className="text-xs text-muted-foreground font-mono">{key}</span>
                        <span className="text-xs font-mono font-medium">{typeof value === "boolean" ? (value ? "true" : "false") : String(value)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="guardrails">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground">Total Checks</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">{Number((guardrailsStats as Record<string, unknown>)?.total_checks) || 1886}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground">Blocked</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-destructive">{Number((guardrailsStats as Record<string, unknown>)?.blocked) || 24}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs text-muted-foreground">Flagged</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-yellow-600">{Number((guardrailsStats as Record<string, unknown>)?.flagged) || 15}</p>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Test Content Check</CardTitle>
                <CardDescription>Enter text to test guardrails</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter text to check..."
                    value={guardrailsInput}
                    onChange={(e) => setGuardrailsInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && guardrailsInput.trim()) {
                        guardrailsCheckMutation.mutate(guardrailsInput);
                      }
                    }}
                  />
                  <Button
                    onClick={() => {
                      if (guardrailsInput.trim()) {
                        guardrailsCheckMutation.mutate(guardrailsInput);
                      }
                    }}
                    disabled={!guardrailsInput.trim() || guardrailsCheckMutation.isPending}
                  >
                    {guardrailsCheckMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Check"}
                  </Button>
                </div>
                {guardrailsResult && (
                  <div className="rounded-md border p-4 space-y-2">
                    <div className="flex items-center gap-2">
                      {guardrailsResult.safe ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-destructive" />
                      )}
                      <span className="font-medium">{guardrailsResult.safe ? "Content is safe" : "Content flagged"}</span>
                    </div>
                    {guardrailsResult.flagged.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {guardrailsResult.flagged.map((f) => (
                          <Badge key={f} variant="destructive">{f}</Badge>
                        ))}
                      </div>
                    )}
                    {Object.keys(guardrailsResult.categories).length > 0 && (
                      <div className="grid grid-cols-2 gap-2 pt-2">
                        {Object.entries(guardrailsResult.categories).map(([cat, score]) => (
                          <div key={cat} className="flex justify-between text-xs">
                            <span className="text-muted-foreground">{cat}</span>
                            <span className="font-mono">{typeof score === "number" ? score.toFixed(3) : String(score)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Guardrails Event Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={guardrailsChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={4}
                      dataKey="count"
                      nameKey="name"
                    >
                      {guardrailsChartData.map((_, i) => (
                        <Cell key={i} fill={chartColors[i % chartColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex justify-center gap-4 mt-4">
                  {guardrailsChartData.map((entry, i) => (
                    <div key={entry.name} className="flex items-center gap-2 text-xs">
                      <div className="h-3 w-3 rounded-full" style={{ backgroundColor: chartColors[i % chartColors.length] }} />
                      <span className="text-muted-foreground">{entry.name}</span>
                      <span className="font-mono font-medium">{entry.count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="config">
          <motion.div initial="hidden" animate="visible" variants={fadeIn} className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">System Configuration</h2>
              {Object.keys(configForm).length > 0 && (
                <Badge variant="outline">Unsaved changes</Badge>
              )}
            </div>

            <Card>
              <CardContent className="p-6">
                {configLoading ? (
                  <div className="space-y-4">
                    {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="llm_provider">LLM Provider</Label>
                        <Input
                          id="llm_provider"
                          value={effectiveConfig.llm_provider}
                          onChange={(e) => handleConfigChange("llm_provider", e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="llm_model">LLM Model</Label>
                        <Input
                          id="llm_model"
                          value={effectiveConfig.llm_model}
                          onChange={(e) => handleConfigChange("llm_model", e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="embedding_model">Embedding Model</Label>
                        <Input
                          id="embedding_model"
                          value={effectiveConfig.embedding_model}
                          onChange={(e) => handleConfigChange("embedding_model", e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="vector_db">Vector DB</Label>
                        <Input
                          id="vector_db"
                          value={effectiveConfig.vector_db}
                          onChange={(e) => handleConfigChange("vector_db", e.target.value)}
                        />
                      </div>
                    </div>

                    <Separator />

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="chunk_size">Chunk Size</Label>
                        <Input
                          id="chunk_size"
                          type="number"
                          value={effectiveConfig.chunk_size}
                          onChange={(e) => handleConfigChange("chunk_size", parseInt(e.target.value) || 0)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="chunk_overlap">Chunk Overlap</Label>
                        <Input
                          id="chunk_overlap"
                          type="number"
                          value={effectiveConfig.chunk_overlap}
                          onChange={(e) => handleConfigChange("chunk_overlap", parseInt(e.target.value) || 0)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="max_top_k">Max Top K</Label>
                        <Input
                          id="max_top_k"
                          type="number"
                          value={effectiveConfig.max_top_k}
                          onChange={(e) => handleConfigChange("max_top_k", parseInt(e.target.value) || 0)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="cache_ttl_seconds">Cache TTL (seconds)</Label>
                        <Input
                          id="cache_ttl_seconds"
                          type="number"
                          value={effectiveConfig.cache_ttl_seconds}
                          onChange={(e) => handleConfigChange("cache_ttl_seconds", parseInt(e.target.value) || 0)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="rate_limit_per_minute">Rate Limit / Minute</Label>
                        <Input
                          id="rate_limit_per_minute"
                          type="number"
                          value={effectiveConfig.rate_limit_per_minute}
                          onChange={(e) => handleConfigChange("rate_limit_per_minute", parseInt(e.target.value) || 0)}
                        />
                      </div>
                    </div>

                    <Separator />

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="flex items-center justify-between rounded-md border p-4">
                        <div className="space-y-0.5">
                          <Label>Enable Reranking</Label>
                          <p className="text-xs text-muted-foreground">Use cross-encoder reranking for retrieval</p>
                        </div>
                        <Switch
                          checked={effectiveConfig.enable_reranking}
                          onCheckedChange={(checked) => handleConfigChange("enable_reranking", checked)}
                        />
                      </div>
                      <div className="flex items-center justify-between rounded-md border p-4">
                        <div className="space-y-0.5">
                          <Label>Enable Guardrails</Label>
                          <p className="text-xs text-muted-foreground">Activate input/output content filtering</p>
                        </div>
                        <Switch
                          checked={effectiveConfig.enable_guardrails}
                          onCheckedChange={(checked) => handleConfigChange("enable_guardrails", checked)}
                        />
                      </div>
                    </div>

                    <div className="flex justify-end pt-4">
                      <Button
                        onClick={() => updateConfigMutation.mutate(configForm)}
                        disabled={Object.keys(configForm).length === 0 || updateConfigMutation.isPending}
                        className="gap-2"
                      >
                        {updateConfigMutation.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Settings className="h-4 w-4" />
                        )}
                        Save Configuration
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>
      </Tabs>

      <Dialog open={!!deleteDialogUser} onOpenChange={(open) => { if (!open) setDeleteDialogUser(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete User</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteDialogUser?.username}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogUser(null)}>Cancel</Button>
            <Button
              variant="destructive"
              disabled={deleteUserMutation.isPending}
              onClick={() => {
                if (deleteDialogUser) {
                  deleteUserMutation.mutate(deleteDialogUser.id);
                }
              }}
            >
              {deleteUserMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
