import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chatService } from "@/services";
import { useStreamingResponse } from "@/hooks";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Send,
  Square,
  Copy,
  RotateCcw,
  ThumbsUp,
  ThumbsDown,
  FileText,
  Sparkles,
  Trash2,
  Pencil,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { filename: string; chunk_text: string; score: number }[];
  isStreaming?: boolean;
}

export default function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [currentSessionId, setCurrentSessionId] = useState(sessionId);
  const [isRenaming, setIsRenaming] = useState(false);
  const [editingTitle, setEditingTitle] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const { content, isStreaming, startStream, stopStream } = useStreamingResponse();

  const { data: existingMessages } = useQuery({
    queryKey: ["messages", currentSessionId],
    queryFn: () => chatService.getMessages(currentSessionId!),
    enabled: !!currentSessionId,
    retry: false,
  });

  useEffect(() => {
    if (existingMessages) {
      setMessages(
        existingMessages.map((m) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
          sources: m.sources,
        })),
      );
    }
  }, [existingMessages]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, content]);

  const createSessionMutation = useMutation({
    mutationFn: (title: string) => chatService.createSession(title),
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      chatService.renameSession(id, title),
    onSuccess: () => {
      toast({ title: "Renamed", description: "Conversation renamed successfully." });
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to rename conversation." });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => chatService.deleteSession(id),
    onSuccess: () => {
      toast({ title: "Deleted", description: "Conversation deleted." });
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      navigate("/chat");
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to delete conversation." });
    },
  });

  useEffect(() => {
    return () => {
      stopStream();
    };
  }, [stopStream]);

  const handleRename = () => {
    if (!editingTitle.trim() || !currentSessionId) return;
    renameMutation.mutate({ id: currentSessionId, title: editingTitle.trim() });
    setIsRenaming(false);
  };

  const handleDelete = () => {
    if (!currentSessionId) return;
    deleteMutation.mutate(currentSessionId);
    setDeleteDialogOpen(false);
  };

  useEffect(() => {
    if (isRenaming && renameInputRef.current) {
      renameInputRef.current.focus();
    }
  }, [isRenaming]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    let sid = currentSessionId;
    if (!sid) {
      try {
        const session = await createSessionMutation.mutateAsync(input.trim().slice(0, 50));
        sid = session.id;
        setCurrentSessionId(sid);
        toast({ title: "Session created", description: "New conversation started." });
      } catch {
        toast({ title: "Error", description: "Failed to create session." });
        setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
        return;
      }
    }

    const assistantMessage: Message = {
      id: `streaming-${Date.now()}`,
      role: "assistant",
      content: "",
      isStreaming: true,
    };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      await startStream({
        query: userMessage.content,
        session_id: sid,
      });
    } catch {
      toast({ title: "Error", description: "Failed to get response." });
      setMessages((prev) => prev.filter((m) => m.id !== assistantMessage.id));
      return;
    }

    queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
  };

  useEffect(() => {
    if (content && !isStreaming) {
      setMessages((prev) =>
        prev.map((m) =>
          m.isStreaming ? { ...m, content, isStreaming: false } : m,
        ),
      );
    }
  }, [content, isStreaming]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleFeedback = async (messageId: string, feedback: "positive" | "negative") => {
    try {
      await chatService.addFeedback(messageId, feedback);
    } catch { /* ignore */ }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          {isRenaming ? (
            <Input
              ref={renameInputRef}
              value={editingTitle}
              onChange={(e) => setEditingTitle(e.target.value)}
              onBlur={handleRename}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleRename();
                if (e.key === "Escape") setIsRenaming(false);
              }}
              className="h-7 w-48 text-sm"
              autoFocus
            />
          ) : (
            <h2 className="font-semibold">Chat</h2>
          )}
          {currentSessionId && !isRenaming && (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => {
                  setEditingTitle("");
                  setIsRenaming(true);
                }}
              >
                <Pencil className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-destructive hover:text-destructive"
                onClick={() => setDeleteDialogOpen(true)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-xs">
            {messages.length} {messages.length === 1 ? "message" : "messages"}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {currentSessionId ? "Session Active" : "New Chat"}
          </Badge>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-4" ref={scrollRef}>
        <div className="mx-auto max-w-3xl py-6 space-y-6" role="log" aria-label="Chat messages" aria-live="polite">
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-20 text-center"
            >
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 mb-4">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Ask anything</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Query your documents with AI-powered retrieval. Ask questions, get accurate answers with source citations.
              </p>
            </motion.div>
          )}

          <AnimatePresence>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className={`max-w-[85%] ${msg.role === "user" ? "" : ""}`}>
                  <Card className={`p-4 ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
                    {msg.role === "assistant" ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content || (msg.isStreaming ? "" : "No response.")}
                        </ReactMarkdown>
                        {msg.isStreaming && (
                          <span className="inline-block h-4 w-2 animate-pulse bg-primary ml-1" />
                        )}
                      </div>
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    )}
                  </Card>

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {msg.sources.map((s, i) => (
                        <Badge key={i} variant="secondary" className="text-xs max-w-[200px] truncate">
                          <FileText className="mr-1 h-3 w-3" />
                          {s.filename} ({(s.score * 100).toFixed(0)}%)
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  {msg.role === "assistant" && !msg.isStreaming && msg.content && (
                    <div className="mt-2 flex gap-1">
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleCopy(msg.content)}>
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleSend()}>
                        <RotateCcw className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleFeedback(msg.id, "positive")}>
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleFeedback(msg.id, "negative")}>
                        <ThumbsDown className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </ScrollArea>

      <Separator />

      {/* Input */}
      <div className="p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="mx-auto max-w-3xl flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.ctrlKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask a question about your documents..."
            disabled={isStreaming}
            className="flex-1"
            aria-label="Message input"
            autoFocus
          />
          {isStreaming ? (
            <Button type="button" variant="destructive" size="icon" aria-label="Stop generation" onClick={stopStream}>
              <Square className="h-4 w-4" />
            </Button>
          ) : (
            <Button type="submit" size="icon" aria-label="Send message" disabled={!input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          )}
        </form>
        <p className="text-center text-xs text-muted-foreground mt-2">
          SecureRAG uses AI to answer questions from your documents. Responses may not always be accurate.
        </p>
      </div>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete conversation</DialogTitle>
            <DialogDescription>
              This action cannot be undone. This will permanently delete this conversation and all its messages.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
