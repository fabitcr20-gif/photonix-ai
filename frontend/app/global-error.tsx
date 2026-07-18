/**
 * Boundary de error para fallos en el layout raíz mismo (muy poco común).
 * A diferencia de error.tsx, este reemplaza <html>/<body> por completo, así
 * que declara su propia estructura HTML mínima con la marca de Photonix AI
 * en vez de dejar la pantalla en blanco por defecto de Next.js.
 */
"use client";

import "./globals.css";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="es" className="dark">
      <body>
        <main className="min-h-screen flex items-center justify-center px-4 py-12 bg-photonix-bg text-photonix-text">
          <div className="w-full max-w-md text-center">
            <p className="text-lg font-semibold tracking-tightish mb-8">
              PHOTONIX <span className="text-photonix-accent">AI</span>
            </p>
            <div className="photonix-card">
              <h1 className="text-xl font-semibold mb-2">Algo salió mal</h1>
              <p className="text-sm text-photonix-textMuted mb-6">
                Ocurrió un error inesperado al cargar la aplicación. No se perdió ningún dato.
              </p>
              <button onClick={reset} className="photonix-btn-primary">
                Reintentar
              </button>
            </div>
          </div>
        </main>
      </body>
    </html>
  );
}
