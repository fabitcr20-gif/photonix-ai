/** Catálogo de Perfiles de Estilo IA disponibles. */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/lib/api";
import type { StyleProfile } from "@/types";

export default function PresetsPage() {
  const [profiles, setProfiles] = useState<StyleProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<StyleProfile[]>("/ai/style-profiles")
      .then(setProfiles)
      .catch(() => setError("No pudimos cargar los presets. Intenta recargar la página."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-1">Presets IA</h1>
      <p className="text-photonix-textMuted mb-6">
        Perfiles de estilo disponibles al procesar una sesión en{" "}
        <Link href="/dashboard/upload" className="text-photonix-accent hover:underline">
          Nueva edición
        </Link>
        .
      </p>

      {loading && <p className="text-photonix-textMuted text-sm">Cargando...</p>}
      {error && <p className="text-sm text-photonix-danger">{error}</p>}

      {!loading && !error && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {profiles.map((p) => (
            <div key={p.id} className="photonix-card">
              <div className="text-2xl mb-2">{p.emoji}</div>
              <p className="font-medium text-sm mb-1">{p.label}</p>
              <p className="text-xs text-photonix-textMuted">{p.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
