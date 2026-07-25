/**
 * Página de Restablecer Contraseña — Photonix AI
 * Se llega aquí desde el enlace del correo de recuperación. Supabase crea
 * automáticamente una sesión de recuperación al cargar esta página (lee el
 * token del propio enlace) -- se escucha el evento PASSWORD_RECOVERY en vez
 * de asumir que ya existe una sesión desde el primer render.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Logo from "@/components/Logo";
import { supabase, updatePassword } from "@/lib/supabaseClient";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY") setReady(true);
    });
    // Si el evento ya disparó antes de montar este listener (carrera posible
    // en la primera carga), una sesión activa aquí también es válida.
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) setReady(true);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setLoading(true);
    try {
      const { error: updateError } = await updatePassword(password);
      if (updateError) throw updateError;
      setDone(true);
      setTimeout(() => router.push("/dashboard"), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar la contraseña.");
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
          {done ? (
            <>
              <h1 className="text-xl font-semibold mb-1">Contraseña actualizada</h1>
              <p className="text-sm text-photonix-textMuted">
                Ya puedes usar tu nueva contraseña. Te llevamos a tu panel...
              </p>
            </>
          ) : !ready ? (
            <>
              <h1 className="text-xl font-semibold mb-1">Verificando enlace...</h1>
              <p className="text-sm text-photonix-textMuted">
                Si este mensaje no cambia en unos segundos, el enlace de recuperación puede
                haber expirado.{" "}
                <Link href="/forgot-password" className="text-photonix-accent hover:underline">
                  Solicita uno nuevo
                </Link>
                .
              </p>
            </>
          ) : (
            <>
              <h1 className="text-xl font-semibold mb-1">Nueva contraseña</h1>
              <p className="text-sm text-photonix-textMuted mb-6">
                Elige una contraseña nueva para tu cuenta.
              </p>

              <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
                <input
                  type="password"
                  placeholder="Nueva contraseña"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  className="photonix-input"
                />
                <input
                  type="password"
                  placeholder="Confirma la nueva contraseña"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                  className="photonix-input"
                />

                {error && <p className="text-sm text-photonix-danger">{error}</p>}

                <button type="submit" disabled={loading} className="photonix-btn-primary mt-2">
                  {loading ? "Guardando..." : "Guardar nueva contraseña"}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
