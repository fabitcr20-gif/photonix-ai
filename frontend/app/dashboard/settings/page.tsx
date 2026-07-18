/** Configuración de la cuenta. */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/lib/api";
import type { Profile } from "@/types";

const PLAN_LABELS: Record<string, string> = {
  trial: "Prueba Gratuita",
  starter: "Photonix Starter",
  pro: "Photonix Pro",
  studio: "Photonix Studio",
  founder: "Fundador (ilimitado)",
};

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Profile>("/auth/me")
      .then(setProfile)
      .catch(() => setError("No pudimos cargar tu configuración. Intenta recargar la página."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold mb-1">Configuración</h1>
      <p className="text-photonix-textMuted mb-6">Datos de tu cuenta y tu plan.</p>

      {loading && <p className="text-photonix-textMuted text-sm mb-4">Cargando...</p>}
      {error && <p className="text-sm text-photonix-danger mb-4">{error}</p>}

      {!loading && !error && (
      <>
      <div className="photonix-card mb-4">
        <h2 className="font-medium mb-4">Cuenta</h2>
        <div className="flex justify-between text-sm py-2 border-b border-photonix-border">
          <span className="text-photonix-textMuted">Nombre</span>
          <span>{profile?.full_name ?? "—"}</span>
        </div>
        <div className="flex justify-between text-sm py-2 border-b border-photonix-border">
          <span className="text-photonix-textMuted">Correo</span>
          <span>{profile?.email ?? "—"}</span>
        </div>
        <div className="flex justify-between text-sm py-2">
          <span className="text-photonix-textMuted">Rol</span>
          <span className="capitalize">{profile?.role ?? "—"}</span>
        </div>
      </div>

      <div className="photonix-card">
        <h2 className="font-medium mb-4">Plan</h2>
        <div className="flex justify-between text-sm py-2 border-b border-photonix-border">
          <span className="text-photonix-textMuted">Plan activo</span>
          <span>{profile?.active_plan ? PLAN_LABELS[profile.active_plan] ?? profile.active_plan : "—"}</span>
        </div>
        <div className="flex justify-between items-center text-sm py-2">
          <span className="text-photonix-textMuted">Gestionar membresía</span>
          <Link href="/dashboard/billing" className="photonix-btn-secondary text-xs px-3 py-1.5">
            Ir a Mi Membresía
          </Link>
        </div>
      </div>
      </>
      )}
    </div>
  );
}
