import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET() {
  try {
    const supabase = await createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    return NextResponse.json({
      accessToken: session?.access_token ?? null,
    });
  } catch {
    return NextResponse.json({ accessToken: null }, { status: 200 });
  }
}
