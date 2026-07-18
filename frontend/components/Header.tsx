/**
 * Encabezado superior del dashboard: plan contratado, acceso rápido a
 * actualizar el plan, notificaciones y avatar del usuario. Deliberadamente
 * liviano (sin repetir el logo, que ya vive en el sidebar) para no
 * sobrecargar la interfaz.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, LifeBuoy, Menu } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { Profile } from "@/types";

const PLAN_LABELS: Record<string, string> = {
  trial: "Prueba Gratuita",
  starter: "Photonix Starter",
  pro: "Photonix Pro",
  studio: "Photonix Studio",
  founder: "Fundador",
};

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/dashboard/upload": "Nueva edición",
  "/dashboard/history": "Historial",
  "/dashboard/exports": "Exportaciones",
  "/dashboard/presets": "Presets IA",
  "/dashboard/watermark": "Marca de agua",
  "/dashboard/billing": "Mi membresía",
  "/dashboard/settings": "Configuración",
  "/dashboard/help": "Ayuda",
  "/dashboard/profile": "Perfil",
};

export default function Header({ title, onMenuClick }: { title?: string; onMenuClick?: () => void }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const pathname = usePathname();
  const resolvedTitle = title ?? PAGE_TITLES[pathname] ?? "Photonix AI";

  useEffect(() => {
    apiGet<Profile>("/auth/me").then(setProfile).catch(() => {});
  }, []);

  const planLabel = profile?.active_plan ? PLAN_LABELS[profile.active_plan] ?? profile.active_plan : null;
  const initial = (profile?.full_name || profile?.email || "?").trim().charAt(0).toUpperCase();

  return (
    <header className="photonix-glass sticky top-0 z-10 flex items-center justify-between gap-3 px-4 sm:px-6 py-3.5">
      <div className="flex items-center gap-3 min-w-0">
        <button onClick={onMenuClick} aria-label="Abrir menú" className="md:hidden p-1.5 -ml-1.5 text-photonix-textMuted hover:text-photonix-text">
          <Menu size={20} />
        </button>
        <h1 className="text-sm font-medium text-photonix-textMuted truncate min-w-0">{resolvedTitle}</h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {planLabel && <span className="photonix-chip hidden md:inline-flex">{planLabel}</span>}
        <Link href="/dashboard/billing" className="photonix-btn-secondary text-sm px-3 py-1.5 hidden sm:inline-flex whitespace-nowrap">
          Actualizar plan
        </Link>
        <Link
          href="/dashboard/help"
          aria-label="Soporte técnico"
          title="Soporte técnico"
          className="p-2 rounded-lg text-photonix-textMuted hover:text-photonix-text hover:bg-white/[0.04] transition-colors"
        >
          <LifeBuoy size={18} />
        </Link>
        <button
          aria-label="Notificaciones"
          className="p-2 rounded-lg text-photonix-textMuted hover:text-photonix-text hover:bg-white/[0.04] transition-colors"
        >
          <Bell size={18} />
        </button>
        <Link
          href="/dashboard/profile"
          aria-label="Mi perfil"
          className="w-8 h-8 rounded-full bg-gradient-to-br from-photonix-accent to-photonix-accent2 flex items-center justify-center text-xs font-semibold text-white shrink-0"
        >
          {initial || "?"}
        </Link>
      </div>
    </header>
  );
}
