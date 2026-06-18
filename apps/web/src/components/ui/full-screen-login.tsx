"use client";

import { Loader2, Mail, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { createClient } from "@/lib/supabase/client";
import { getSupabaseConfig } from "@/lib/supabase/config";

type AuthMode = "signin" | "signup";

export const FullScreenLogin = () => {
  const { toast } = useToast();
  const [mode, setMode] = useState<AuthMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isPasswordLoading, setIsPasswordLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  const isAuthConfigured = Boolean(getSupabaseConfig());

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const error = params.get("error");
    const notice = params.get("notice");

    if (error) {
      toast({
        title: "Sign in failed",
        description: error,
        variant: "destructive",
      });
      window.history.replaceState({}, "", "/login");
    }

    if (notice) {
      toast({
        title: "Check your email",
        description: notice,
      });
      window.history.replaceState({}, "", "/login");
    }
  }, [toast]);

  function showMissingConfigToast() {
    toast({
      title: "Supabase auth is not configured",
      description: "Add a valid NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to enable login.",
      variant: "destructive",
    });
  }

  function handlePasswordAuth(event: FormEvent<HTMLFormElement>) {
    if (!isAuthConfigured) {
      event.preventDefault();
      showMissingConfigToast();
      return;
    }

    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      event.preventDefault();
      toast({
        title: "Email and password are required",
        description: "Enter both fields before continuing.",
        variant: "destructive",
      });
      return;
    }

    // Keep fields enabled during native form submission; disabled inputs are omitted from FormData.
  }

  async function handleGoogleLogin() {
    if (!isAuthConfigured) {
      showMissingConfigToast();
      return;
    }

    setIsGoogleLoading(true);

    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (error) {
        toast({
          title: "Google sign in failed",
          description: error.message,
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "Google sign in failed",
        description: "Supabase auth could not be started.",
        variant: "destructive",
      });
    } finally {
      setIsGoogleLoading(false);
    }
  }

  const passwordButtonLabel =
    mode === "signin"
      ? isPasswordLoading
        ? "Signing in..."
        : "Sign in"
      : isPasswordLoading
        ? "Creating account..."
        : "Create account";

  return (
    <div className="flex min-h-screen items-center justify-center overflow-hidden bg-[#f4f4f4] p-4">
      <div className="relative flex w-full max-w-5xl flex-col overflow-hidden rounded-[20px] border border-neutral-200 bg-white shadow-2xl md:flex-row">
        <div className="relative min-h-[360px] overflow-hidden bg-neutral-950 p-8 text-white md:w-1/2 md:p-12">
          <div className="absolute inset-0 z-10 bg-gradient-to-t from-black/90 to-black/10" />
          <div className="absolute inset-0 z-0 flex overflow-hidden opacity-20">
            <div className="h-[40rem] w-[4rem] translate-x-10 -skew-x-12 bg-gradient-to-r from-transparent via-white to-transparent opacity-30" />
            <div className="h-[40rem] w-[4rem] translate-x-32 -skew-x-12 bg-gradient-to-r from-transparent via-white to-transparent opacity-30" />
            <div className="h-[40rem] w-[4rem] translate-x-56 -skew-x-12 bg-gradient-to-r from-transparent via-white to-transparent opacity-30" />
          </div>
          <div className="absolute -bottom-10 -left-10 z-0 h-[15rem] w-[15rem] rounded-full bg-neutral-800" />
          <div className="absolute bottom-20 right-10 z-0 h-[5rem] w-[8rem] rounded-full bg-neutral-700 blur-xl" />

          <div className="relative z-20 flex h-full flex-col justify-end">
            <h1 className="text-3xl font-medium leading-tight tracking-normal md:text-4xl">
              Your intelligent workspace companion.
            </h1>
            <p className="mt-4 max-w-md text-sm leading-6 text-neutral-300 md:text-base">
              Secure workspace chat with memory, document context, web retrieval, and research-grade answers.
            </p>
          </div>
        </div>

        <div className="z-20 flex bg-white p-8 text-neutral-900 md:w-1/2 md:p-12">
          <div className="m-auto w-full max-w-sm">
            <div className="mb-8">
              <div className="mb-5 inline-flex rounded-xl border border-neutral-200 bg-neutral-100 p-3 text-neutral-900 shadow-sm">
                <Sparkles className="h-7 w-7" />
              </div>
              <h2 className="text-3xl font-medium tracking-normal">Welcome back</h2>
              <p className="mt-2 text-sm leading-6 text-neutral-500">
                Sign in with your email and password to continue.
              </p>
            </div>

            <Tabs value={mode} onValueChange={(value) => setMode(value as AuthMode)} className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="signin">Sign in</TabsTrigger>
                <TabsTrigger value="signup">Create account</TabsTrigger>
              </TabsList>

              <TabsContent value="signin" className="mt-5">
                <form
                  action="/auth/password"
                  className="space-y-4"
                  method="post"
                  onSubmit={handlePasswordAuth}
                >
                  <input name="mode" type="hidden" value="signin" />
                  <AuthFields
                    email={email}
                    password={password}
                    isLoading={isPasswordLoading}
                    passwordAutocomplete="current-password"
                    onEmailChange={setEmail}
                    onPasswordChange={setPassword}
                  />
                  <Button className="w-full" type="submit" disabled={isPasswordLoading}>
                    {isPasswordLoading ? <Loader2 className="animate-spin" /> : <Mail />}
                    {passwordButtonLabel}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="signup" className="mt-5">
                <form
                  action="/auth/password"
                  className="space-y-4"
                  method="post"
                  onSubmit={handlePasswordAuth}
                >
                  <input name="mode" type="hidden" value="signup" />
                  <AuthFields
                    email={email}
                    password={password}
                    isLoading={isPasswordLoading}
                    passwordAutocomplete="new-password"
                    onEmailChange={setEmail}
                    onPasswordChange={setPassword}
                  />
                  <Button className="w-full" type="submit" disabled={isPasswordLoading}>
                    {isPasswordLoading ? <Loader2 className="animate-spin" /> : <Mail />}
                    {passwordButtonLabel}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>

            <div className="my-6 grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-xs text-neutral-400">
              <div className="h-px bg-neutral-200" />
              <span>or</span>
              <div className="h-px bg-neutral-200" />
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={handleGoogleLogin}
              disabled={isGoogleLoading}
            >
              {isGoogleLoading ? (
                <Loader2 className="animate-spin" />
              ) : (
                <svg className="h-4 w-4 rounded-full bg-white" viewBox="0 0 24 24" aria-hidden>
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
              )}
              {isGoogleLoading ? "Opening Google..." : "Continue with Google"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

function AuthFields({
  email,
  password,
  isLoading,
  passwordAutocomplete,
  onEmailChange,
  onPasswordChange,
}: {
  email: string;
  password: string;
  isLoading: boolean;
  passwordAutocomplete: "current-password" | "new-password";
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
}) {
  return (
    <>
      <div className="space-y-2">
        <label className="text-sm font-medium text-neutral-800" htmlFor="email">
          Email
        </label>
        <Input
          id="email"
          name="email"
          autoComplete="email"
          inputMode="email"
          placeholder="you@example.com"
          required
          type="email"
          value={email}
          disabled={isLoading}
          onChange={(event) => onEmailChange(event.target.value)}
        />
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium text-neutral-800" htmlFor="password">
          Password
        </label>
        <Input
          id="password"
          name="password"
          autoComplete={passwordAutocomplete}
          minLength={6}
          placeholder="Enter your password"
          type="password"
          required
          value={password}
          disabled={isLoading}
          onChange={(event) => onPasswordChange(event.target.value)}
        />
      </div>
    </>
  );
}
