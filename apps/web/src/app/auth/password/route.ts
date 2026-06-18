import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { getSupabaseConfig } from "@/lib/supabase/config";

type AuthMode = "signin" | "signup";

type AuthBody = {
  mode: AuthMode;
  email: string;
  password: string;
};

type CookieToSet = {
  name: string;
  value: string;
  options: CookieOptions;
};

type CookieToRemove = {
  name: string;
  options: CookieOptions;
};

function loginRedirect(request: NextRequest, key: "error" | "notice", message: string) {
  const url = new URL("/login", request.url);
  url.searchParams.set(key, message);
  return NextResponse.redirect(url, 303);
}

function attachCookies(response: NextResponse, cookiesToSet: CookieToSet[]) {
  cookiesToSet.forEach(({ name, value, options }) => {
    response.cookies.set(name, value, options);
  });
  return response;
}

async function parseAuthBody(request: NextRequest): Promise<{ body: AuthBody; wantsJson: boolean }> {
  const contentType = request.headers.get("content-type") ?? "";
  const wantsJson = contentType.includes("application/json");

  if (wantsJson) {
    const json = (await request.json()) as Partial<AuthBody>;
    return {
      wantsJson,
      body: {
        mode: json.mode === "signup" ? "signup" : "signin",
        email: json.email?.trim() ?? "",
        password: json.password ?? "",
      },
    };
  }

  const formData = await request.formData();
  const mode = formData.get("mode");
  const email = formData.get("email");
  const password = formData.get("password");

  return {
    wantsJson,
    body: {
      mode: mode === "signup" ? "signup" : "signin",
      email: typeof email === "string" ? email.trim() : "",
      password: typeof password === "string" ? password : "",
    },
  };
}

function authError(request: NextRequest, wantsJson: boolean, message: string, status = 400) {
  if (wantsJson) {
    return NextResponse.json({ error: message }, { status });
  }
  return loginRedirect(request, "error", message);
}

export async function POST(request: NextRequest) {
  let parsed: { body: AuthBody; wantsJson: boolean };

  try {
    parsed = await parseAuthBody(request);
  } catch {
    return authError(request, true, "Invalid auth request body.");
  }

  const {
    body: { mode, email, password },
    wantsJson,
  } = parsed;

  if (!email || !password) {
    return authError(request, wantsJson, "Email and password are required.");
  }

  if (password.length < 6) {
    return authError(request, wantsJson, "Password must be at least 6 characters.");
  }

  const config = getSupabaseConfig();

  if (!config) {
    return authError(request, wantsJson, "Supabase auth is not configured for this environment.", 500);
  }

  try {
    const cookiesToSet: CookieToSet[] = [];
    const cookiesToRemove: CookieToRemove[] = [];
    const supabase = createServerClient(config.url, config.anonKey, {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          request.cookies.set(name, value);
          cookiesToSet.push({ name, value, options });
        },
        remove(name: string, options: CookieOptions) {
          request.cookies.set(name, "");
          cookiesToRemove.push({ name, options });
        },
      },
    });

    const authResult =
      mode === "signin"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({
            email,
            password,
            options: {
              emailRedirectTo: new URL("/auth/callback", request.url).toString(),
            },
          });

    if (authResult.error) {
      return authError(request, wantsJson, authResult.error.message, 401);
    }

    if (mode === "signup" && !authResult.data.session) {
      if (wantsJson) {
        return NextResponse.json({ ok: true, requiresConfirmation: true });
      }
      return loginRedirect(request, "notice", "Check your email to confirm your account, then sign in.");
    }

    const response = wantsJson
      ? NextResponse.json({ ok: true, redirectTo: "/" })
      : NextResponse.redirect(new URL("/", request.url), 303);

    cookiesToRemove.forEach(({ name, options }) => {
      response.cookies.set(name, "", { ...options, maxAge: 0 });
    });

    return attachCookies(response, cookiesToSet);
  } catch (error) {
    return authError(
      request,
      wantsJson,
      error instanceof Error ? error.message : "Authentication failed. Please try again.",
      500,
    );
  }
}
