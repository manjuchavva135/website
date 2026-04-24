import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json(
    {
      service: "web",
      status: "ok",
      environment: process.env.NODE_ENV ?? "development",
    },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
