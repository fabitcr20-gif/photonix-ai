import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: "Photonix AI — Edición Fotográfica Automatizada con IA",
  description:
    "Photonix AI ayuda a fotógrafos y diseñadores profesionales a editar sesiones completas de fotos automáticamente con Inteligencia Artificial.",
  // El favicon y el apple-touch-icon se generan por convención de archivo
  // (app/icon.svg, app/apple-icon.tsx) -- Next.js los enlaza automáticamente,
  // no hace falta declararlos aquí.
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`dark ${inter.variable}`}>
      <body>{children}</body>
    </html>
  );
}
