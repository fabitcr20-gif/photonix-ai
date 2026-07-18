/** Barra lateral de navegación del dashboard de cliente. */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Sparkles,
  History,
  Download,
  Palette,
  Image as ImageIcon,
  CreditCard,
  Settings,
  HelpCircle,
  User,
  ShieldCheck,
  LogOut,
} from "lucide-react";
import { X } from "lucide-react";
import Logo from "./Logo";
import { signOut } from "@/lib/supabaseClient";
import { apiGet } from "@/lib/api";
import type { Profile } from "@/types";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/upload", label: "Nueva edición", icon: Sparkles },
  { href: "/dashboard/history", label: "Historial", icon: History },
  { href: "/dashboard/exports", label: "Exportaciones", icon: Download },
  { href: "/dashboard/presets", label: "Presets IA", icon: Palette },
  { href: "/dashboard/watermark", label: "Marca de agua", icon: ImageIcon },
  { href: "/dashboard/billing", label: "Mi membresía", icon: CreditCard },
  { href: "/dashboard/settings", label: "Configuración", icon: Settings },
  { href: "/dashboard/help", label: "Ayuda", icon: HelpCircle },
  { href: "/dashboard/profile", label: "Perfil", icon: User },
];

export default function Sidebar({
  mobileOpen = false,
  onClose,
}: {
  mobileOpen?: boolean;
  onClose?: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    apiGet<Profile>("/auth/me").then(setProfile).catch(() => {});
  }, []);

  const isAdmin = profile?.role === "admin";

  return (
    <>
      {/* Fondo oscuro detrás del sidebar en móvil, para cerrarlo al tocar afuera */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/60 z-30 md:hidden" onClick={onClose} aria-hidden="true" />
      )}

      <aside
        className={`w-64 shrink-0 h-screen fixed md:sticky top-0 z-40 bg-photonix-surface border-r border-photonix-border flex flex-col p-4 transition-transform duration-200 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="mb-6 px-2 pt-1 flex items-center justify-between">
          <Logo size="sm" />
          <button onClick={onClose} aria-label="Cerrar menú" className="md:hidden p-1 text-photonix-textMuted hover:text-photonix-text">
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 flex flex-col gap-0.5 overflow-y-auto">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                className={`photonix-nav-item ${active ? "photonix-nav-item-active" : "photonix-nav-item-inactive"}`}
              >
                <Icon size={17} strokeWidth={active ? 2.25 : 2} />
                {label}
              </Link>
            );
          })}
        </nav>

        {isAdmin && (
          <Link
            href="/admin"
            onClick={onClose}
            className="photonix-nav-item photonix-nav-item-inactive !text-photonix-accent mt-2"
          >
            <ShieldCheck size={17} />
            Panel de administrador
          </Link>
        )}

        <button
          onClick={async () => {
            await signOut();
            router.push("/login");
          }}
          className="photonix-nav-item photonix-nav-item-inactive hover:!text-photonix-danger mt-2"
        >
          <LogOut size={17} />
          Cerrar sesión
        </button>
      </aside>
    </>
  );
}
