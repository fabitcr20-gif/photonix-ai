/**
 * Página de Registro — Photonix AI
 * Soporta: Google OAuth, Apple ID y Correo/Contraseña manual.
 * El checkbox de Términos y Condiciones es obligatorio para poder registrarse.
 * Al completar el registro se llama a /auth/complete-registration en el
 * backend, que crea el perfil, arranca el trial gratuito de 30 días y
 * detecta automáticamente al fundador/administrador por su correo.
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Logo from "@/components/Logo";
import OAuthButtons from "@/components/OAuthButtons";
import TermsCheckbox from "@/components/TermsCheckbox";
import { signUpWithEmail } from "@/lib/supabaseClient";
import { apiPostJson } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);

    if (!acceptedTerms) {
      setError("Debes aceptar los Términos y Condiciones para continuar.");
      return;
    }

    setLoading(true);
    try {
      const { data, error: signUpError } = await signUpWithEmail(email, password, fullName);
      if (signUpError) throw signUpError;

      if (!data.session) {
        // Supabase exige confirmar el correo antes de dar una sesión activa:
        // sin sesión no podemos llamar todavía al backend (necesita el token).
        // El perfil se crea automáticamente en cuanto inicie sesión por
        // primera vez (ver GET /auth/me en el backend).
        setInfo(
          "Te enviamos un correo de confirmación a " +
            email +
            ". Ábrelo y confirma tu cuenta, luego inicia sesión."
        );
        setLoading(false);
        return;
      }

      await apiPostJson("/auth/complete-registration", {
        email,
        password,
        full_name: fullName,
        accepted_terms: acceptedTerms,
      });

      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ocurrió un error al registrarte.");
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
          <h1 className="text-xl font-semibold mb-1">Crea tu cuenta</h1>
          <p className="text-sm text-photonix-textMuted mb-6">
            1 mes de prueba gratuita con acceso completo. Sin tarjeta requerida.
          </p>

          <TermsCheckbox checked={acceptedTerms} onChange={setAcceptedTerms} />

          <div className="mt-4">
            <OAuthButtons
              acceptedTerms={acceptedTerms}
              onBlocked={() => setError("Debes aceptar los Términos y Condiciones para continuar.")}
            />
          </div>

          <div className="flex items-center gap-3 my-5">
            <div className="h-px bg-photonix-border flex-1" />
            <span className="text-xs text-photonix-textMuted">o con tu correo</span>
            <div className="h-px bg-photonix-border flex-1" />
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
            <input
              type="text"
              placeholder="Nombre completo"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              className="photonix-input"
            />
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
              placeholder="Contraseña (mínimo 8 caracteres)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
              className="photonix-input"
            />

            {error && <p className="text-sm text-photonix-danger">{error}</p>}
            {info && <p className="text-sm text-photonix-accent">{info}</p>}

            <button type="submit" disabled={loading} className="photonix-btn-primary mt-2">
              {loading ? "Creando cuenta..." : "Crear cuenta gratis"}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-photonix-textMuted mt-6">
          ¿Ya tienes cuenta?{" "}
          <Link href="/login" className="text-photonix-accent hover:underline">
            Inicia sesión
          </Link>
        </p>
      </div>
    </main>
  );
}
