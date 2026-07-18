import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import { useMediaQuery, useNotifications } from "@/hooks";
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  History,
  Settings,
  Shield,
  BarChart3,
  LogOut,
  Menu,
  X,
  ChevronLeft,
  Search,
  Bell,
  Check,
  CheckCheck,
  Moon,
  Sun,
  Monitor,
  Brain,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme } from "@/lib/theme-provider";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Chat", href: "/chat", icon: MessageSquare },
  { name: "Documents", href: "/documents", icon: FileText },
  { name: "History", href: "/history", icon: History },
  { name: "Settings", href: "/settings", icon: Settings },
];

const adminNavigation = [
  { name: "Security", href: "/admin/security", icon: Shield },
  { name: "Monitoring", href: "/admin/monitoring", icon: BarChart3 },
  { name: "Evaluation", href: "/admin/evaluation", icon: Brain },
];

export const Sidebar = React.memo(function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const isMobile = useMediaQuery("(max-width: 768px)");

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
    : user?.email?.slice(0, 2).toUpperCase() ?? "U";

  const sidebar = (
    <div
      role="banner"
      className={cn(
        "flex h-full flex-col border-r bg-card transition-all duration-300",
        collapsed ? "w-16" : "w-64",
        isMobile && "w-64",
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center justify-between border-b px-4">
        {!collapsed && (
          <Link to="/dashboard" className="flex items-center gap-2">
            <Brain className="h-6 w-6 text-primary" />
            <span className="font-semibold text-lg">SecureRAG</span>
          </Link>
        )}
        {collapsed && <Brain className="h-6 w-6 text-primary mx-auto" />}
        {!isMobile && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setCollapsed(!collapsed)}
          >
            <ChevronLeft
              className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")}
            />
          </Button>
        )}
        {isMobile && (
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setMobileOpen(false)}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Search */}
      {!collapsed && (
        <div className="p-3">
          <button
            className="flex w-full items-center gap-2 rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground hover:bg-accent"
            onClick={() => {
              // Future: command palette
            }}
          >
            <Search className="h-4 w-4" />
            <span>Search...</span>
            <kbd className="ml-auto text-xs bg-background border rounded px-1">⌘K</kbd>
          </button>
        </div>
      )}

      {/* Navigation */}
      <nav role="navigation" aria-label="Main navigation" className="flex-1 space-y-1 p-2">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.name}
              to={item.href}
              onClick={() => isMobile && setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                collapsed && "justify-center px-2",
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span>{item.name}</span>}
            </Link>
          );
        })}

        {user?.role === "admin" && (
          <>
            <div className={cn("my-2 border-t", collapsed ? "mx-2" : "")} />
            {!collapsed && (
              <p className="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider" aria-label="Admin navigation">
                Admin
              </p>
            )}
            {adminNavigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => isMobile && setMobileOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    collapsed && "justify-center px-2",
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span>{item.name}</span>}
                </Link>
              );
            })}
          </>
        )}
      </nav>

      {/* Theme Toggle */}
      <div className={cn("border-t p-2", collapsed && "px-2")}>
        <div className={cn("flex gap-1", collapsed ? "flex-col" : "justify-center")}>
          <Button
            variant={theme === "light" ? "secondary" : "ghost"}
            size="icon"
            className="h-8 w-8"
            onClick={() => setTheme("light")}
          >
            <Sun className="h-4 w-4" />
          </Button>
          <Button
            variant={theme === "dark" ? "secondary" : "ghost"}
            size="icon"
            className="h-8 w-8"
            onClick={() => setTheme("dark")}
          >
            <Moon className="h-4 w-4" />
          </Button>
          <Button
            variant={theme === "system" ? "secondary" : "ghost"}
            size="icon"
            className="h-8 w-8"
            onClick={() => setTheme("system")}
          >
            <Monitor className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* User */}
      <div className="border-t p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex w-full items-center gap-3 rounded-md p-2 hover:bg-accent">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs">{initials}</AvatarFallback>
              </Avatar>
              {!collapsed && (
                <div className="flex-1 text-left">
                  <p className="text-sm font-medium truncate">{user?.full_name || user?.username}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                </div>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuItem onClick={() => navigate("/settings")}>
              <Settings className="mr-2 h-4 w-4" /> Profile
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-destructive">
              <LogOut className="mr-2 h-4 w-4" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile hamburger */}
      {isMobile && (
        <div className="fixed top-0 left-0 z-50 flex h-14 items-center border-b bg-background px-4">
          <Button variant="ghost" size="icon" aria-label="Sidebar" onClick={() => setMobileOpen(true)}>
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2 ml-2">
            <Brain className="h-5 w-5 text-primary" />
            <span className="font-semibold">SecureRAG</span>
          </div>
        </div>
      )}

      {/* Mobile overlay */}
      {isMobile && mobileOpen && (
        <div className="fixed inset-0 z-50 bg-black/50" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar */}
      {isMobile ? (
        <div
          className={cn(
            "fixed inset-y-0 left-0 z-50 transform transition-transform duration-200",
            mobileOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          {sidebar}
        </div>
      ) : (
        <div className="hidden md:block">{sidebar}</div>
      )}
    </>
  );
});

export const Topbar = React.memo(function Topbar() {
  const { notifications, unreadCount, markRead, markAllRead, dismiss } = useNotifications();

  const timeAgo = (dateStr: string) => {
    const now = Date.now();
    const date = new Date(dateStr).getTime();
    const diff = now - date;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  };

  return (
    <div className="flex h-14 items-center justify-between border-b bg-background px-4 md:px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold" />
      </div>
      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8 relative">
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground px-1">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <div className="flex items-center justify-between p-3">
              <span className="text-sm font-semibold">Notifications</span>
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs gap-1"
                  onClick={() => markAllRead()}
                >
                  <CheckCheck className="h-3.5 w-3.5" />
                  Mark all read
                </Button>
              )}
            </div>
            <DropdownMenuSeparator />
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
                <Bell className="h-8 w-8" />
                <span className="text-sm">No notifications</span>
              </div>
            ) : (
              notifications.slice(0, 10).map((n) => (
                <DropdownMenuItem
                  key={n.id}
                  className={cn(
                    "flex items-start gap-3 p-3 cursor-default",
                    !n.read && "border-l-2 border-l-primary bg-accent/30",
                  )}
                  onSelect={(e) => e.preventDefault()}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{n.title}</span>
                      <span className="text-xs text-muted-foreground shrink-0">
                        {timeAgo(n.created_at)}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                      {n.message}
                    </p>
                  </div>
                  <div className="flex flex-col gap-1 shrink-0 pt-0.5">
                    {!n.read && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => markRead(n.id)}
                      >
                        <Check className="h-3 w-3" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-muted-foreground hover:text-destructive"
                      onClick={() => dismiss(n.id)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                </DropdownMenuItem>
              ))
            )}
            {notifications.length > 10 && (
              <>
                <DropdownMenuSeparator />
                <div className="p-2 text-center">
                  <span className="text-xs text-muted-foreground">
                    +{notifications.length - 10} more
                  </span>
                </div>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
});

export function AppLayout({ children }: { children: React.ReactNode }) {
  const isMobile = useMediaQuery("(max-width: 768px)");
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        {isMobile && <div className="h-14" />}
        <main id="main-content" role="main" className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
