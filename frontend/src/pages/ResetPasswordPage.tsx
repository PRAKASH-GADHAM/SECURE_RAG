import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Brain, Loader2, CheckCircle } from "lucide-react";
import { motion } from "framer-motion";

const schema = z.object({
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirmPassword: z.string(),
}).refine((d) => d.password === d.confirmPassword, { message: "Passwords don't match", path: ["confirmPassword"] });
type Form = z.infer<typeof schema>;

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [success, setSuccess] = useState(false);
  const token = searchParams.get("token") || "";

  const form = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { password: "", confirmPassword: "" } });

  const mutation = useMutation({
    mutationFn: async (data: Form) => {
      await api.post("/api/v1/auth/password-reset/confirm", { token, password: data.password });
    },
    onSuccess: () => setSuccess(true),
  });

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-md">
          <Card>
            <CardHeader className="text-center">
              <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
              <CardTitle className="mt-4">Password Reset</CardTitle>
              <CardDescription>Your password has been reset.</CardDescription>
            </CardHeader>
            <CardFooter>
              <Button className="w-full" onClick={() => navigate("/login")}>Go to Login</Button>
            </CardFooter>
          </Card>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <Card>
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
                <Brain className="h-6 w-6 text-primary-foreground" />
              </div>
            </div>
            <CardTitle className="text-2xl">Reset password</CardTitle>
            <CardDescription>Enter your new password below.</CardDescription>
          </CardHeader>
          <form onSubmit={form.handleSubmit((d) => mutation.mutate(d))}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="password">New Password</Label>
                <Input id="password" type="password" placeholder="••••••••" {...form.register("password")} />
                {form.formState.errors.password && <p className="text-xs text-destructive">{form.formState.errors.password.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input id="confirmPassword" type="password" placeholder="••••••••" {...form.register("confirmPassword")} />
                {form.formState.errors.confirmPassword && <p className="text-xs text-destructive">{form.formState.errors.confirmPassword.message}</p>}
              </div>
            </CardContent>
            <CardFooter>
              <Button type="submit" className="w-full" disabled={mutation.isPending || !token}>
                {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Reset Password
              </Button>
            </CardFooter>
          </form>
        </Card>
      </motion.div>
    </div>
  );
}
