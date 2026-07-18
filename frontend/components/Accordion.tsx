/** Acordeón minimalista reutilizable (ej. "Opciones avanzadas"). */
"use client";

import { useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

export default function Accordion({
  title,
  subtitle,
  children,
  defaultOpen = false,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const contentRef = useRef<HTMLDivElement>(null);

  return (
    <div className="border border-photonix-border rounded-xl2 overflow-hidden bg-photonix-surface">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div>
          <p className="font-medium text-sm">{title}</p>
          {subtitle && <p className="text-xs text-photonix-textMuted mt-0.5">{subtitle}</p>}
        </div>
        <ChevronDown
          size={18}
          className={`text-photonix-textMuted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>
      <div
        style={{
          maxHeight: open ? contentRef.current?.scrollHeight ?? 1000 : 0,
        }}
        className="transition-[max-height] duration-300 ease-in-out overflow-hidden"
      >
        <div ref={contentRef} className="px-5 pb-5">
          {children}
        </div>
      </div>
    </div>
  );
}
