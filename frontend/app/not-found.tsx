/** Página 404 personalizada (con la marca de Photonix AI, no la genérica de Next.js). */
import Link from "next/link";
import Logo from "@/components/Logo";

export default function NotFound() {
  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md text-center">
        <div className="flex justify-center mb-8">
          <Logo size="md" />
        </div>
        <div className="photonix-card">
          <p className="text-5xl font-semibold mb-3 text-photonix-accent">404</p>
          <h1 className="text-xl font-semibold mb-2">Página no encontrada</h1>
          <p className="text-sm text-photonix-textMuted mb-6">
            El enlace que seguiste no existe o se movió de lugar.
          </p>
          <Link href="/dashboard" className="photonix-btn-primary inline-block">
            Volver al panel principal
          </Link>
        </div>
      </div>
    </main>
  );
}
