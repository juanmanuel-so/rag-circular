import { NextResponse } from "next/server";

export async function GET() {
  const baseUrl =
    process.env.API_INTERNAL_URL ??
    "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${baseUrl}/openapi.json`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        { connected: false, status: response.status },
        { status: 502 }
      );
    }

    const api = await response.json();

    return NextResponse.json({
      connected: true,
      backend: api.info?.title,
      endpoints: Object.keys(api.paths ?? {}),
    });
  } catch (error) {
    return NextResponse.json(
      {
        connected: false,
        error: error instanceof Error
          ? error.message
          : "Error desconocido",
      },
      { status: 502 }
    );
  }
}