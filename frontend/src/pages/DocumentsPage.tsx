import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { documentService } from "@/services";
import type { Document } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
import {
  Upload,
  Search,
  Trash2,
  FileText,
  Eye,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  CheckSquare,
  Square,
  Filter,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatusIcon({ status }: { status: Document["status"] }) {
  switch (status) {
    case "completed":
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case "processing":
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case "failed":
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-yellow-500" />;
  }
}

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);
  const [deleteDoc, setDeleteDoc] = useState<Document | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [fileTypeFilter, setFileTypeFilter] = useState("all");
  const [batchDeleteDoc, setBatchDeleteDoc] = useState<boolean>(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const prevStatusesRef = useRef<Record<string, string>>({});

  const { data: documents, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: documentService.list,
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      setIsUploading(true);
      setUploadProgress(0);
      const formData = new FormData();
      formData.append("file", file);
      const { api } = await import("@/services/api");
      const res = await api.post("/api/v1/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded * 100) / e.total));
        },
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setIsUploading(false);
      setUploadProgress(0);
      toast({ title: "Upload complete", description: "Your document has been uploaded successfully." });
    },
    onError: () => {
      setIsUploading(false);
      toast({ title: "Upload failed", description: "Failed to upload the document.", variant: "destructive" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: documentService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setDeleteDoc(null);
      toast({ title: "Document deleted", description: "The document has been deleted." });
    },
    onError: () => {
      toast({ title: "Delete failed", description: "Failed to delete the document.", variant: "destructive" });
    },
  });

  const batchDeleteMutation = useMutation({
    mutationFn: async (ids: string[]) => {
      await Promise.all(ids.map((id) => documentService.delete(id)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setSelectedDocs(new Set());
      setBatchDeleteDoc(false);
      toast({ title: "Documents deleted", description: "Selected documents have been deleted." });
    },
    onError: () => {
      toast({ title: "Delete failed", description: "Failed to delete some documents.", variant: "destructive" });
    },
  });

  useEffect(() => {
    if (!documents) return;
    const hasProcessing = documents.some((d) => d.status === "processing");
    if (!hasProcessing) return;
    const interval = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    }, 5000);
    return () => clearInterval(interval);
  }, [documents, queryClient]);

  useEffect(() => {
    if (!documents) return;
    documents.forEach((doc) => {
      const prev = prevStatusesRef.current[doc.id];
      if (prev === "processing" && doc.status === "completed") {
        toast({ title: "Processing complete", description: `${doc.original_filename} has been processed.` });
      }
    });
    const newStatuses: Record<string, string> = {};
    documents.forEach((d) => { newStatuses[d.id] = d.status; });
    prevStatusesRef.current = newStatuses;
  }, [documents, toast]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadMutation.mutate(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadMutation.mutate(file);
  };

  const toggleSelectDoc = (id: string) => {
    setSelectedDocs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredDocs = documents?.filter(
    (d) =>
      (fileTypeFilter === "all" || d.file_type.toLowerCase().includes(fileTypeFilter)) &&
      (d.original_filename.toLowerCase().includes(search.toLowerCase()) ||
        d.file_type.toLowerCase().includes(search.toLowerCase())),
  );

  return (
    <div
      className={`p-6 space-y-6 min-h-[calc(100vh-64px)] transition-colors ${isDragOver ? "bg-primary/5 border-2 border-dashed border-primary" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Documents</h1>
          <p className="text-muted-foreground">Manage your uploaded documents</p>
        </div>
        <Button onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
          {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
          Upload
        </Button>
        <input ref={fileInputRef} type="file" className="hidden" accept=".pdf,.docx,.txt,.md" aria-label="File upload" onChange={handleFileSelect} />
      </div>

      {isUploading && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <div className="flex-1">
                <p className="text-sm font-medium">Uploading...</p>
                <Progress value={uploadProgress} className="mt-2" />
              </div>
              <span className="text-sm text-muted-foreground">{uploadProgress}%</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search */}
      <div className="flex items-center gap-3 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            aria-label="Search documents"
          />
        </div>
        <Select value={fileTypeFilter} onValueChange={setFileTypeFilter}>
          <SelectTrigger className="w-[130px]">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue placeholder="File type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="pdf">PDF</SelectItem>
            <SelectItem value="docx">DOCX</SelectItem>
            <SelectItem value="txt">TXT</SelectItem>
            <SelectItem value="md">MD</SelectItem>
          </SelectContent>
        </Select>
        {selectedDocs.size > 0 && (
          <Button variant="destructive" onClick={() => setBatchDeleteDoc(true)}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete Selected ({selectedDocs.size})
          </Button>
        )}
      </div>

      {/* Document list */}
      <ScrollArea className="h-[calc(100vh-320px)]">
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="grid" aria-label="Document list">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="pt-6">
                  <div className="h-4 bg-muted rounded w-1/2 mb-2" />
                  <div className="h-3 bg-muted rounded w-1/3" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredDocs?.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No documents</h3>
            <p className="text-sm text-muted-foreground">Upload your first document to get started.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="grid" aria-label="Document list">
            <AnimatePresence>
              {filteredDocs?.map((doc) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                >
                  <Card className="group hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => toggleSelectDoc(doc.id)}
                            className="shrink-0 mt-0.5"
                          >
                            {selectedDocs.has(doc.id) ? (
                              <CheckSquare className="h-4 w-4 text-primary" />
                            ) : (
                              <Square className="h-4 w-4 text-muted-foreground" />
                            )}
                          </button>
                          <CardTitle className="text-sm font-medium truncate pr-2">
                            {doc.original_filename}
                          </CardTitle>
                        </div>
                        <StatusIcon status={doc.status} />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{doc.file_type.toUpperCase()}</span>
                          <span>{formatFileSize(doc.file_size)}</span>
                        </div>
                        {doc.status === "processing" && <Progress value={doc.progress * 100} />}
                        {doc.status === "completed" && (
                          <Badge variant="secondary" className="text-xs">
                            {doc.chunk_count} chunks
                          </Badge>
                        )}
                        {doc.status === "failed" && doc.error_message && (
                          <p className="text-xs text-destructive truncate">{doc.error_message}</p>
                        )}
                        <p className="text-xs text-muted-foreground">
                          {new Date(doc.created_at).toLocaleDateString()}
                        </p>
                        <div className="flex gap-1 pt-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => setPreviewDoc(doc)}
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-destructive hover:text-destructive"
                            onClick={() => setDeleteDoc(doc)}
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

      {/* Preview dialog */}
      <Dialog open={!!previewDoc} onOpenChange={() => setPreviewDoc(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {previewDoc?.original_filename}
            </DialogTitle>
            <DialogDescription>
              {previewDoc?.file_type.toUpperCase()} — {formatFileSize(previewDoc?.file_size ?? 0)} — {previewDoc?.chunk_count} chunks
            </DialogDescription>
          </DialogHeader>
          <div className="text-sm text-muted-foreground">
            <p>Preview is available for processed documents with chunk content.</p>
            <p className="mt-2">Status: <Badge variant={previewDoc?.status === "completed" ? "default" : "secondary"}>{previewDoc?.status}</Badge></p>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete dialog */}
      <Dialog open={!!deleteDoc} onOpenChange={() => setDeleteDoc(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteDoc?.original_filename}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDoc(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => deleteDoc && deleteMutation.mutate(deleteDoc.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Batch delete dialog */}
      <Dialog open={batchDeleteDoc} onOpenChange={() => setBatchDeleteDoc(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Documents</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{selectedDocs.size}</strong> selected document(s)? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBatchDeleteDoc(false)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => batchDeleteMutation.mutate(Array.from(selectedDocs))}
              disabled={batchDeleteMutation.isPending}
            >
              {batchDeleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete All
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
