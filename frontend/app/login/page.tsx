/**
 * Página de Inicio de Sesión — Photonix AI
 * Soporta Google OAuth, Apple ID y Correo/Contraseña.
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Logo from "@/components/Logo";
import OAuthButtons from "@/components/OAuthButtons";
import { signInWithEmail } from "@/lib/supabaseClient";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { error: signInError } = await signInWithEmail(email, password);
      if (signInError) throw signInError;
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Correo o contraseña incorrectos.");
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
          <h1 className="text-xl font-semibold mb-1">Bienvenido de vuelta</h1>
          <p className="text-sm text-photonix-textMuted mb-6">
            Inicia sesión para continuar editando tus sesiones.
          </p>

          <OAuthButtons />

          <div className="flex items-center gap-3 my-5">
            <div className="h-px bg-photonix-border flex-1" />
            <span className="text-xs text-photonix-textMuted">o con tu correo</span>
            <div className="h-px bg-photonix-border flex-1" />
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
            <input
              type="email"
              placeholder="Correo electrónico"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="photonix-input"
            />
            <input
              type="password"
              placeholder="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="photonix-input"
            />

            {error && <p className="text-sm text-photonix-danger">{error}</p>}

            <button type="submit" disabled={loading} className="photonix-btn-primary mt-2">
              {loading ? "Ingresando..." : "Iniciar sesión"}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-photonix-textMuted mt-6">
          ¿No tienes cuenta?{" "}
          <Link href="/register" className="text-photonix-accent hover:underline">
            Regístrate gratis
          </Link>
        </p>
      </div>
    </main>
  );
}
