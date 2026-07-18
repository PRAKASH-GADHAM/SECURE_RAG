import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Brain, Loader2, CheckCircle, ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";

const schema = z.object({ email: z.string().email("Invalid email") });
type Form = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [success, setSuccess] = useState(false);

  const form = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { email: "" } });

  const mutation = useMutation({
    mutationFn: async (data: Form) => {
      await api.post("/api/v1/auth/password-reset/request", data);
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
              <CardTitle className="mt-4">Check your email</CardTitle>
              <CardDescription>We sent a password reset link to your email.</CardDescription>
            </CardHeader>
            <CardFooter>
              <Link to="/login" className="w-full">
                <Button variant="outline" className="w-full"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Login</Button>
              </Link>
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
            <CardTitle className="text-2xl">Forgot password?</CardTitle>
            <CardDescription>Enter your email and we will send a reset link.</CardDescription>
          </CardHeader>
          <form onSubmit={form.handleSubmit((d) => mutation.mutate(d))}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" placeholder="you@example.com" {...form.register("email")} />
                {form.formState.errors.email && <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>}
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-4">
              <Button type="submit" className="w-full" disabled={mutation.isPending}>
                {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Send Reset Link
              </Button>
              <Link to="/login" className="text-sm text-primary hover:underline">Back to login</Link>
            </CardFooter>
          </form>
        </Card>
      </motion.div>
    </div>
  );
}
