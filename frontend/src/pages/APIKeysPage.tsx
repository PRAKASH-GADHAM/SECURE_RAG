import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiKeyService } from "@/services";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Key, Plus, Trash2, Copy, Loader2 } from "lucide-react";

export default function APIKeysPage() {
  const queryClient = useQueryClient();
  const [newKeyName, setNewKeyName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [deleteKey, setDeleteKey] = useState<{ id: string; name: string } | null>(null);

  const { data: keys, isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: apiKeyService.list,
  });

  const createMutation = useMutation({
    mutationFn: apiKeyService.create,
    onSuccess: (data) => {
      setCreatedKey(data.key);
      setNewKeyName("");
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: apiKeyService.revoke,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      setDeleteKey(null);
    },
  });

  const copyToClipboard = (text: string) => navigator.clipboard.writeText(text);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">API Keys</h1>
          <p className="text-muted-foreground">Manage API keys for programmatic access</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" /> Create Key
        </Button>
      </div>

      {createdKey && (
        <Card className="border-green-500/50 bg-green-500/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-green-600">API Key Created</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-muted px-3 py-2 text-xs font-mono break-all">{createdKey}</code>
              <Button variant="ghost" size="icon" onClick={() => copyToClipboard(createdKey)}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">Copy this key now. It will not be shown again.</p>
          </CardContent>
        </Card>
      )}

      <ScrollArea className="h-[calc(100vh-280px)]">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => <Card key={i} className="animate-pulse h-20" />)}
          </div>
        ) : keys?.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Key className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No API keys</h3>
            <p className="text-sm text-muted-foreground">Create an API key to access the API programmatically.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {keys?.map((key) => (
              <Card key={key.id}>
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-medium">{key.name}</h3>
                        <Badge variant={key.is_active ? "default" : "secondary"} className="text-xs">
                          {key.is_active ? "Active" : "Revoked"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 font-mono">{key.key_prefix}••••••••</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Created: {new Date(key.created_at).toLocaleDateString()}
                        {key.last_used_at && ` • Last used: ${new Date(key.last_used_at).toLocaleDateString()}`}
                      </p>
                    </div>
                    {key.is_active && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteKey({ id: key.id, name: key.name })}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Create dialog */}
      <Dialog open={showCreate} onOpenChange={() => setShowCreate(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>Give your key a descriptive name.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="key-name">Name</Label>
              <Input
                id="key-name"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="e.g., Production API Key"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button
              onClick={() => createMutation.mutate(newKeyName)}
              disabled={!newKeyName.trim() || createMutation.isPending}
            >
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete dialog */}
      <Dialog open={!!deleteKey} onOpenChange={() => setDeleteKey(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke API Key</DialogTitle>
            <DialogDescription>Revoke <strong>{deleteKey?.name}</strong>? This cannot be undone.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteKey(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => deleteKey && deleteMutation.mutate(deleteKey.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Revoke
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
