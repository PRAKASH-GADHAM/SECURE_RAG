import React, { Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { AppLayout } from "@/components/layout";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";

const LoginPage = React.lazy(() => import("@/pages/LoginPage"));
const RegisterPage = React.lazy(() => import("@/pages/RegisterPage"));
const ForgotPasswordPage = React.lazy(() => import("@/pages/ForgotPasswordPage"));
const ResetPasswordPage = React.lazy(() => import("@/pages/ResetPasswordPage"));
const DashboardPage = React.lazy(() => import("@/pages/DashboardPage"));
const ChatPage = React.lazy(() => import("@/pages/ChatPage"));
const DocumentsPage = React.lazy(() => import("@/pages/DocumentsPage"));
const HistoryPage = React.lazy(() => import("@/pages/HistoryPage"));
const SettingsPage = React.lazy(() => import("@/pages/SettingsPage"));
const APIKeysPage = React.lazy(() => import("@/pages/APIKeysPage"));
const AdminPage = React.lazy(() => import("@/pages/AdminPage"));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <AppLayout>{children}</AppLayout>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <TooltipProvider>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:bg-background focus:p-4 focus:ring-2 focus:ring-primary"
      >
        Skip to main content
      </a>
      <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>}>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
        <Route path="/forgot-password" element={<PublicRoute><ForgotPasswordPage /></PublicRoute>} />
        <Route path="/reset-password" element={<PublicRoute><ResetPasswordPage /></PublicRoute>} />

        {/* Protected routes */}
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
        <Route path="/chat/:sessionId" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
        <Route path="/documents" element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        <Route path="/settings/api-keys" element={<ProtectedRoute><APIKeysPage /></ProtectedRoute>} />

        {/* Admin routes */}
        <Route path="/admin/security" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
        <Route path="/admin/monitoring" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
        <Route path="/admin/evaluation" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />

        {/* Redirects */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      </Suspense>
      <Toaster />
    </TooltipProvider>
  );
}
