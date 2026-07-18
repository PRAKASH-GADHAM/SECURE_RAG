import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { chatService } from "@/services";
import type { ChatSession } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Search, MessageSquare, Trash2, Download, Plus, Clock, Loader2, Pencil, ArrowUpDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function HistoryPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [deleteSession, setDeleteSession] = useState<ChatSession | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [sort, setSort] = useState<"newest" | "oldest" | "title">("newest");
  const { toast } = useToast();

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: chatService.listSessions,
  });

  const deleteMutation = useMutation({
    mutationFn: chatService.deleteSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      setDeleteSession(null);
      toast({ title: "Deleted", description: "Conversation deleted." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to delete conversation.", variant: "destructive" });
    },
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      chatService.renameSession(id, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      setEditingId(null);
      toast({ title: "Renamed", description: "Conversation renamed." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to rename conversation.", variant: "destructive" });
    },
  });

  const filteredSessions = sessions
    ?.filter((s) => s.title?.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sort === "newest") return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      if (sort === "oldest") return new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
      return (a.title || "").localeCompare(b.title || "");
    });

  const exportChat = (session: ChatSession) => {
    chatService.getMessages(session.id).then((messages) => {
      const content = messages
        .map((m) => `[${m.role}] ${m.content}`)
        .join("\n\n");
      const blob = new Blob([content], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${session.title || "chat"}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">History</h1>
          <p className="text-muted-foreground">Your conversation history</p>
        </div>
        <Button onClick={() => navigate("/chat")}>
          <Plus className="mr-2 h-4 w-4" /> New Chat
        </Button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={sort} onValueChange={(v) => setSort(v as typeof sort)}>
          <SelectTrigger className="w-[160px]">
            <ArrowUpDown className="mr-2 h-4 w-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="newest">Newest first</SelectItem>
            <SelectItem value="oldest">Oldest first</SelectItem>
            <SelectItem value="title">By title</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <ScrollArea className="h-[calc(100vh-280px)]">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="py-4">
                  <div className="h-4 bg-muted rounded w-1/3 mb-2" />
                  <div className="h-3 bg-muted rounded w-1/4" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredSessions?.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <MessageSquare className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No conversations</h3>
            <p className="text-sm text-muted-foreground">Start a chat to see your history here.</p>
            <Button className="mt-4" onClick={() => navigate("/chat")}>
              <Plus className="mr-2 h-4 w-4" /> Start a Chat
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {filteredSessions?.map((session) => (
                <motion.div
                  key={session.id}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                >
                  <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => editingId !== session.id && navigate(`/chat/${session.id}`)}>
                    <CardContent className="py-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          {editingId === session.id ? (
                            <Input
                              value={editingTitle}
                              onChange={(e) => setEditingTitle(e.target.value)}
                              onBlur={() => {
                                if (editingTitle.trim()) {
                                  renameMutation.mutate({ id: session.id, title: editingTitle.trim() });
                                } else {
                                  setEditingId(null);
                                }
                              }}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.currentTarget.blur();
                                } else if (e.key === "Escape") {
                                  setEditingId(null);
                                }
                              }}
                              autoFocus
                              className="h-7 text-sm"
                              onClick={(e) => e.stopPropagation()}
                            />
                          ) : (
                            <h3 className="text-sm font-medium truncate">{session.title || "Untitled Chat"}</h3>
                          )}
                          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span>{new Date(session.updated_at).toLocaleString()}</span>
                          </div>
                        </div>
                        <div className="flex gap-1 ml-4">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingId(session.id);
                              setEditingTitle(session.title || "");
                            }}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => { e.stopPropagation(); exportChat(session); }}
                          >
                            <Download className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-destructive hover:text-destructive"
                            onClick={(e) => { e.stopPropagation(); setDeleteSession(session); }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </ScrollArea>

      <Dialog open={!!deleteSession} onOpenChange={() => setDeleteSession(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Conversation</DialogTitle>
            <DialogDescription>
              Delete <strong>{deleteSession?.title || "this conversation"}</strong>? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteSession(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => deleteSession && deleteMutation.mutate(deleteSession.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
