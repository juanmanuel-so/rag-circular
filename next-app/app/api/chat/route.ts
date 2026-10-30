import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  // MVP: no authentication. Add NextAuth/Auth.js or equivalent before public deployment.
  let body: unknown;
  try { body = await request.json(); } catch { return NextResponse.json({ error: 'JSON inválido' }, { status: 400 }); }
  if (!body || typeof body !== 'object' || !('question' in body) ||
      typeof body.question !== 'string' || body.question.trim().length < 3 || body.question.length > 2000) {
    return NextResponse.json({ error: 'Pregunta inválida' }, { status: 400 });
  }
  try {
    const response = await fetch(`${process.env.RAG_API_URL}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': process.env.RAG_API_KEY ?? '' },
      body: JSON.stringify({ question: body.question, top_k: 5 }),
      cache: 'no-store',
      signal: AbortSignal.timeout(60000),
    });
    if (!response.ok) return NextResponse.json({ error: 'Servicio RAG no disponible' }, { status: 502 });
    return NextResponse.json(await response.json(), { headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return NextResponse.json({ error: 'Error al conectar con el servicio RAG' }, { status: 502 });
  }
}
