/** Tarjeta premium de selección de Perfil de Estilo IA (Retrato, Automotriz, etc.). */
"use client";

import type { StyleProfile } from "@/types";

const IMPROVEMENT_LABELS: Record<StyleProfile["improvement_level"], string> = {
  adaptativo: "Adaptativo",
  sutil: "Mejora sutil",
  moderado: "Mejora moderada",
  alto: "Mejora alta",
};

export default function StyleProfileCard({
  profile,
  selected,
  onSelect,
}: {
  profile: StyleProfile;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      className={`text-left p-4 rounded-xl2 border transition-all duration-200 ${
        selected
          ? "border-transparent bg-gradient-to-br from-photonix-accent/20 to-photonix-accent2/10 shadow-[0_0_0_1px_rgba(124,108,246,0.55)]"
          : "border-photonix-border bg-photonix-surface hover:border-photonix-steel/50 hover:-translate-y-0.5"
      }`}
    >
      <div className="text-2xl mb-2">{profile.emoji}</div>
      <p className="font-medium text-sm mb-1">{profile.label}</p>
      <p className="text-xs text-photonix-textMuted mb-3 line-clamp-2">{profile.description}</p>
      <div className="flex items-center justify-between text-[11px] text-photonix-textMuted">
        <span>~{profile.estimated_seconds_per_photo}s/foto</span>
        <span>{IMPROVEMENT_LABELS[profile.improvement_level]}</span>
      </div>
    </button>
  );
}
