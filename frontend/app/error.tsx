/**
 * Boundary de error de Next.js para toda la app (excepto el layout raíz, que
 * usa global-error.tsx). Reemplaza la pantalla de error genérica de Next por
 * una con la marca de Photonix AI y un botón para reintentar.
 */
"use client";

import { useEffect } from "react";
import Link from "next/link";
import Logo from "@/components/Logo";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Error no controlado:", error);
  }, [error]);

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md text-center">
        <div className="flex justify-center mb-8">
          <Logo size="md" />
        </div>
        <div className="photonix-card">
          <h1 className="text-xl font-semibold mb-2">Algo salió mal</h1>
          <p className="text-sm text-photonix-textMuted mb-6">
            Ocurrió un error inesperado. No se perdió ningún dato — puedes intentarlo de nuevo.
          </p>
          <div className="flex flex-col sm:flex-row gap-2 justify-center">
            <button onClick={reset} className="photonix-btn-primary">
              Reintentar
            </button>
            <Link href="/dashboard" className="photonix-btn-secondary">
              Volver al panel principal
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
