/** Barra lateral exclusiva del Panel de Administrador (fundador/desarrollador). */
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BarChart3, ShieldCheck, BellRing, LifeBuoy, Users, MessageSquareHeart, ArrowLeftCircle, LogOut } from "lucide-react";
import Logo from "./Logo";
import { signOut } from "@/lib/supabaseClient";

const links = [
  { href: "/admin", label: "Estadísticas", icon: BarChart3 },
  { href: "/admin/validations", label: "Validación SINPE", icon: ShieldCheck },
  { href: "/admin/users", label: "Usuarios", icon: Users },
  { href: "/admin/reminders", label: "Recordatorios", icon: BellRing },
  { href: "/admin/support", label: "Soporte", icon: LifeBuoy },
  { href: "/admin/feedback", label: "Retroalimentación", icon: MessageSquareHeart },
];

export default function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside className="w-64 shrink-0 h-screen sticky top-0 bg-photonix-navy border-r border-photonix-border flex flex-col p-5">
      <div className="mb-2 px-1">
        <Logo size="sm" />
      </div>
      <p className="text-xs text-photonix-steel px-1 mb-6">Panel de Administrador</p>

      <nav className="flex-1 flex flex-col gap-0.5">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`photonix-nav-item ${active ? "photonix-nav-item-active" : "photonix-nav-item-inactive"}`}
            >
              <Icon size={17} strokeWidth={active ? 2.25 : 2} />
              {label}
            </Link>
          );
        })}
      </nav>

      <Link href="/dashboard" className="photonix-nav-item photonix-nav-item-inactive !text-photonix-accent mb-1">
        <ArrowLeftCircle size={18} />
        Volver al panel principal
      </Link>

      <button
        onClick={async () => {
          await signOut();
          router.push("/login");
        }}
        className="photonix-nav-item photonix-nav-item-inactive hover:!text-photonix-danger"
      >
        <LogOut size={18} />
        Cerrar sesión
      </button>
    </aside>
  );
}
