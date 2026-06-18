import { createClient } from "@/lib/supabase/client";
import { getSupabaseConfig } from "@/lib/supabase/config";

type SessionTokenResponse = {
  accessToken?: string | null;
};

export async function getAuthToken(token?: string) {
  if (token) {
    return token;
  }

  if (typeof window === "undefined" || !getSupabaseConfig()) {
    return undefined;
  }

  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  if (data.session?.access_token) {
    return data.session.access_token;
  }

  const response = await fetch("/auth/session", {
    cache: "no-store",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    return undefined;
  }

  const session = (await response.json()) as SessionTokenResponse;
  return session.accessToken ?? undefined;
}
