import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useTheme } from "@/lib/theme-provider";
import { Loader2, User, Key, Palette, Bot, Save } from "lucide-react";
import { motion } from "framer-motion";

const profileSchema = z.object({
  full_name: z.string().optional(),
  username: z.string().min(3),
});
type ProfileForm = z.infer<typeof profileSchema>;

const passwordSchema = z.object({
  current_password: z.string().min(1),
  new_password: z.string().min(8),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, { message: "Passwords don't match", path: ["confirm_password"] });
type PasswordForm = z.infer<typeof passwordSchema>;

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  const profileForm = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name || "", username: user?.username || "" },
  });

  const passwordForm = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  const updateProfileMutation = useMutation({
    mutationFn: async (data: ProfileForm) => {
      const res = await api.put("/api/v1/auth/me", data);
      return res.data;
    },
    onSuccess: (data) => {
      updateUser(data);
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: async (data: PasswordForm) => {
      await api.post("/api/v1/auth/change-password", {
        current_password: data.current_password,
        new_password: data.new_password,
      });
    },
    onSuccess: () => {
      setPasswordSuccess(true);
      passwordForm.reset();
      setTimeout(() => setPasswordSuccess(false), 3000);
    },
  });

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList>
          <TabsTrigger value="profile" className="gap-2"><User className="h-4 w-4" /> Profile</TabsTrigger>
          <TabsTrigger value="password" className="gap-2"><Key className="h-4 w-4" /> Password</TabsTrigger>
          <TabsTrigger value="appearance" className="gap-2"><Palette className="h-4 w-4" /> Appearance</TabsTrigger>
          <TabsTrigger value="model" className="gap-2"><Bot className="h-4 w-4" /> Model</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardHeader>
                <CardTitle>Profile</CardTitle>
                <CardDescription>Update your personal information</CardDescription>
              </CardHeader>
              <form onSubmit={profileForm.handleSubmit((d) => updateProfileMutation.mutate(d))}>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input value={user?.email || ""} disabled />
                    <p className="text-xs text-muted-foreground">Email cannot be changed.</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="username">Username</Label>
                    <Input id="username" {...profileForm.register("username")} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="full_name">Full Name</Label>
                    <Input id="full_name" {...profileForm.register("full_name")} />
                  </div>
                </CardContent>
                <CardFooter>
                  <Button type="submit" disabled={updateProfileMutation.isPending}>
                    {updateProfileMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    <Save className="mr-2 h-4 w-4" /> Save Changes
                  </Button>
                </CardFooter>
              </form>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="password">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardHeader>
                <CardTitle>Change Password</CardTitle>
                <CardDescription>Update your password regularly for security</CardDescription>
              </CardHeader>
              <form onSubmit={passwordForm.handleSubmit((d) => changePasswordMutation.mutate(d))}>
                <CardContent className="space-y-4">
                  {passwordSuccess && (
                    <div className="rounded-md bg-green-500/10 p-3 text-sm text-green-600">Password changed successfully.</div>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="current_password">Current Password</Label>
                    <Input id="current_password" type="password" {...passwordForm.register("current_password")} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="new_password">New Password</Label>
                    <Input id="new_password" type="password" {...passwordForm.register("new_password")} />
                    {passwordForm.formState.errors.new_password && (
                      <p className="text-xs text-destructive">{passwordForm.formState.errors.new_password.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm_password">Confirm New Password</Label>
                    <Input id="confirm_password" type="password" {...passwordForm.register("confirm_password")} />
                    {passwordForm.formState.errors.confirm_password && (
                      <p className="text-xs text-destructive">{passwordForm.formState.errors.confirm_password.message}</p>
                    )}
                  </div>
                </CardContent>
                <CardFooter>
                  <Button type="submit" disabled={changePasswordMutation.isPending}>
                    {changePasswordMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    <Key className="mr-2 h-4 w-4" /> Change Password
                  </Button>
                </CardFooter>
              </form>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="appearance">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardHeader>
                <CardTitle>Appearance</CardTitle>
                <CardDescription>Customize the look and feel</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Dark Mode</p>
                    <p className="text-xs text-muted-foreground">Toggle between light and dark theme</p>
                  </div>
                  <Switch
                    checked={theme === "dark"}
                    onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
                  />
                </div>
                <Separator />
                <div>
                  <p className="text-sm font-medium mb-3">Theme Preference</p>
                  <div className="flex gap-3">
                    {(["light", "dark", "system"] as const).map((t) => (
                      <Button
                        key={t}
                        variant={theme === t ? "default" : "outline"}
                        onClick={() => setTheme(t)}
                        className="capitalize"
                      >
                        {t}
                      </Button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="model">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardHeader>
                <CardTitle>Model Selection</CardTitle>
                <CardDescription>Configure AI model preferences</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Retrieval Mode</Label>
                  <div className="flex gap-3">
                    {["hybrid", "dense", "bm25"].map((mode) => (
                      <Button key={mode} variant="outline" className="capitalize">{mode}</Button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Top K Results</Label>
                  <Input type="number" defaultValue={5} min={1} max={20} className="max-w-[120px]" />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Enable Reranking</p>
                    <p className="text-xs text-muted-foreground">Use cross-encoder for result reranking</p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
