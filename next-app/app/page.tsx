'use client';
import { FormEvent, useState } from 'react';

type Source = { document: string; page: number | null; chunk_index: number; score: number; excerpt: string };
type Message = { question: string; answer: string; sources: Source[] };

export default function Home() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  async function send(e: FormEvent) {
    e.preventDefault();
    if (loading || question.trim().length < 3) return;
    const q = question.trim(); setLoading(true); setError(''); setQuestion('');
    try {
      const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q }) });
      if (!res.ok) throw new Error('No fue posible obtener respuesta');
      const data = await res.json();
      setMessages(old => [...old, { question: q, answer: data.answer, sources: data.sources }]);
    } catch (e) { setError(e instanceof Error ? e.message : 'Error inesperado'); }
    finally { setLoading(false); }
  }
  return <main>
    <h1>Asistente de Economía Circular</h1>
    <p>Consulta los documentos disponibles en la plataforma.</p>
    {messages.map((m, i) => <article key={i} style={{ border: '1px solid #ddd', padding: 16, borderRadius: 8, marginBottom: 16 }}>
      <strong>Pregunta:</strong><p>{m.question}</p><strong>Respuesta:</strong><p style={{ whiteSpace: 'pre-wrap' }}>{m.answer}</p>
      <details><summary>Fuentes ({m.sources.length})</summary><ul>{m.sources.map((s, j) => <li key={j}><strong>{s.document}</strong>{s.page ? ` · página ${s.page}` : ''} · fragmento {s.chunk_index}<p>{s.excerpt}</p></li>)}</ul></details>
    </article>)}
    <form onSubmit={send} style={{ display: 'flex', gap: 8 }}>
      <input aria-label="Pregunta" value={question} onChange={e => setQuestion(e.target.value)} maxLength={2000} placeholder="Escribe tu pregunta..." style={{ flex: 1, padding: 12 }} />
      <button disabled={loading || question.trim().length < 3}>{loading ? 'Consultando...' : 'Enviar'}</button>
    </form>
    {error && <p role="alert" style={{ color: 'crimson' }}>{error}</p>}
  </main>;
}
