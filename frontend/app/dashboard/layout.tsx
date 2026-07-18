"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import AuthGate from "@/components/AuthGate";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <AuthGate>
      <div className="flex min-h-screen bg-photonix-bg">
        <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
        <div className="flex-1 flex flex-col min-w-0">
          <Header onMenuClick={() => setMobileOpen(true)} />
          <div className="flex-1 p-4 sm:p-8">{children}</div>
        </div>
      </div>
    </AuthGate>
  );
}
