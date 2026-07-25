/**
 * Página de Recuperación de Contraseña — Photonix AI
 * Envía el correo de recuperación vía Supabase Auth (enlace lleva a /reset-password).
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import Logo from "@/components/Logo";
import { resetPasswordForEmail } from "@/lib/supabaseClient";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { error: resetError } = await resetPasswordForEmail(email);
      if (resetError) throw resetError;
      // Siempre mostramos el mismo mensaje de éxito exista o no esa cuenta --
      // así no se puede usar este formulario para averiguar qué correos están
      // registrados en Photonix AI.
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar el correo. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <Logo size="md" />
        </div>

        <div className="photonix-card">
          {sent ? (
            <>
              <h1 className="text-xl font-semibold mb-1">Revisa tu correo</h1>
              <p className="text-sm text-photonix-textMuted">
                Si <strong>{email}</strong> tiene una cuenta en Photonix AI, te enviamos un
                enlace para restablecer tu contraseña. Puede tardar unos minutos en llegar.
              </p>
            </>
          ) : (
            <>
              <h1 className="text-xl font-semibold mb-1">¿Olvidaste tu contraseña?</h1>
              <p className="text-sm text-photonix-textMuted mb-6">
                Ingresa tu correo y te enviamos un enlace para restablecerla.
              </p>

              <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
                <input
                  type="email"
                  placeholder="Correo electrónico"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="photonix-input"
                />

                {error && <p className="text-sm text-photonix-danger">{error}</p>}

                <button type="submit" disabled={loading} className="photonix-btn-primary mt-2">
                  {loading ? "Enviando..." : "Enviar enlace de recuperación"}
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-sm text-photonix-textMuted mt-6">
          <Link href="/login" className="text-photonix-accent hover:underline">
            Volver a iniciar sesión
          </Link>
        </p>
      </div>
    </main>
  );
}
