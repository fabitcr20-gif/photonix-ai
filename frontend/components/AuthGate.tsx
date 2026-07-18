/**
 * Protege rutas privadas: mientras verifica la sesión de Supabase muestra un
 * loader, y si no hay sesión redirige a /login en vez de dejar pasar a los
 * hijos (que antes se renderizaban vacíos con "—" al fallar sus propios
 * fetch con 401). `requireAdmin` además exige profile.role === "admin",
 * consultado con el mismo /auth/me que ya usa Sidebar.tsx.
 */
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { apiGet } from "@/lib/api";
import Logo from "./Logo";
import type { Profile } from "@/types";

function FullScreenLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-photonix-bg">
      <div className="flex flex-col items-center gap-4">
        <Logo size="sm" />
        <div className="w-5 h-5 rounded-full border-2 border-photonix-border border-t-photonix-accent animate-spin" />
      </div>
    </div>
  );
}

export default function AuthGate({
  children,
  requireAdmin = false,
}: {
  children: React.ReactNode;
  requireAdmin?: boolean;
}) {
  const router = useRouter();
  const [status, setStatus] = useState<"checking" | "allowed">("checking");

  useEffect(() => {
    let active = true;

    async function check() {
      const { data } = await supabase.auth.getSession();
      if (!active) return;

      if (!data.session) {
        router.replace("/login");
        return;
      }

      if (requireAdmin) {
        try {
          const profile = await apiGet<Profile>("/auth/me");
          if (!active) return;
          if (profile.role !== "admin") {
            router.replace("/dashboard");
            return;
          }
        } catch {
          if (!active) return;
          router.replace("/dashboard");
          return;
        }
      }

      setStatus("allowed");
    }

    check();

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) router.replace("/login");
    });

    return () => {
      active = false;
      subscription.subscription.unsubscribe();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === "checking") return <FullScreenLoader />;
  return <>{children}</>;
}
