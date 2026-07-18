/** Perfil del usuario. */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api";
import { signOut } from "@/lib/supabaseClient";
import type { Profile } from "@/types";

const PLAN_LABELS: Record<string, string> = {
  trial: "Prueba Gratuita",
  starter: "Photonix Starter",
  pro: "Photonix Pro",
  studio: "Photonix Studio",
  founder: "Fundador",
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    apiGet<Profile>("/auth/me")
      .then(setProfile)
      .catch(() => setError("No pudimos cargar tu perfil. Intenta recargar la página."))
      .finally(() => setLoading(false));
  }, []);

  const initial = (profile?.full_name || profile?.email || "?").trim().charAt(0).toUpperCase();

  return (
    <div className="max-w-md">
      <h1 className="text-2xl font-semibold mb-6">Perfil</h1>

      {loading && <p className="text-photonix-textMuted text-sm mb-4">Cargando...</p>}
      {error && <p className="text-sm text-photonix-danger mb-4">{error}</p>}

      {!loading && !error && (
        <div className="photonix-card flex flex-col items-center text-center">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-photonix-accent to-photonix-accent2 flex items-center justify-center text-2xl font-semibold text-white mb-4">
            {initial || "?"}
          </div>
          <p className="font-medium">{profile?.full_name ?? "—"}</p>
          <p className="text-sm text-photonix-textMuted mb-1">{profile?.email ?? "—"}</p>
          {profile?.role === "admin" && (
            <span className="photonix-chip mt-2">Fundador / Administrador</span>
          )}

          <div className="w-full mt-6 pt-4 border-t border-photonix-border flex flex-col gap-2">
            <div className="flex justify-between text-sm">
              <span className="text-photonix-textMuted">Plan</span>
              <span>{profile?.active_plan ? PLAN_LABELS[profile.active_plan] ?? profile.active_plan : "—"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-photonix-textMuted">Fin de prueba gratuita</span>
              <span>
                {profile?.trial_ends_at ? new Date(profile.trial_ends_at).toLocaleDateString("es-CR") : "—"}
              </span>
            </div>
            <Link href="/dashboard/billing" className="text-sm text-photonix-accent hover:underline text-right mt-1">
              Gestionar membresía
            </Link>
          </div>

          <button
            onClick={async () => {
              await signOut();
              router.push("/login");
            }}
            className="photonix-btn-secondary mt-6 w-full"
          >
            Cerrar sesión
          </button>
        </div>
      )}
    </div>
  );
}
