import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { geo_id } = body;

  if (!geo_id || !/^GSE\d+$/i.test(geo_id)) {
    return NextResponse.json(
      { detail: "Invalid GEO accession ID. Must match GSE followed by digits." },
      { status: 400 }
    );
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  try {
    const response = await fetch(`${API_URL}/api/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session?.access_token}`,
      },
      body: JSON.stringify({ geo_id: geo_id.toUpperCase() }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || "Analysis submission failed" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { detail: "Failed to connect to analysis service" },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const jobId = searchParams.get("jobId");

  if (!jobId) {
    return NextResponse.json(
      { detail: "jobId parameter is required" },
      { status: 400 }
    );
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  try {
    const response = await fetch(`${API_URL}/api/analyze/${jobId}`, {
      headers: {
        Authorization: `Bearer ${session?.access_token}`,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || "Failed to fetch job status" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { detail: "Failed to connect to analysis service" },
      { status: 502 }
    );
  }
}
