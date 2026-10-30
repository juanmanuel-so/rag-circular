import type { ReactNode } from 'react';
export const metadata = { title: 'Asistente de Economía Circular' };
export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="es"><body style={{ fontFamily: 'system-ui', maxWidth: 850, margin: '2rem auto', padding: '0 1rem' }}>{children}</body></html>;
}
