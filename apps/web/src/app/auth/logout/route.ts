import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { getSupabaseConfig } from "@/lib/supabase/config";

type CookieChange = {
  name: string;
  value: string;
  options: CookieOptions;
};

export async function POST(request: NextRequest) {
  const response = NextResponse.redirect(new URL("/login", request.url), 303);
  const config = getSupabaseConfig();

  if (!config) {
    return response;
  }

  const cookieChanges: CookieChange[] = [];
  const supabase = createServerClient(config.url, config.anonKey, {
    cookies: {
      get(name: string) {
        return request.cookies.get(name)?.value;
      },
      set(name: string, value: string, options: CookieOptions) {
        cookieChanges.push({ name, value, options });
      },
      remove(name: string, options: CookieOptions) {
        cookieChanges.push({ name, value: "", options: { ...options, maxAge: 0 } });
      },
    },
  });

  await supabase.auth.signOut();
  cookieChanges.forEach(({ name, value, options }) => {
    response.cookies.set(name, value, options);
  });

  return response;
}
