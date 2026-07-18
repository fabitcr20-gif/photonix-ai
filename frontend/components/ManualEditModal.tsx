/** Edición manual de UNA foto individual (no afecta el resto del lote). */
"use client";

import { useState } from "react";
import { X, Loader2 } from "lucide-react";
import LabeledSlider from "@/components/LabeledSlider";
import { apiPostJson } from "@/lib/api";

interface ManualEditPayload {
  exposure: number;
  highlights: number;
  shadows: number;
  whites: number;
  blacks: number;
  clarity: number;
  saturation: number;
  dehaze: number;
  contrast: number;
  temperature: number;
}

const ZERO: ManualEditPayload = {
  exposure: 0,
  highlights: 0,
  shadows: 0,
  whites: 0,
  blacks: 0,
  clarity: 0,
  saturation: 0,
  dehaze: 0,
  contrast: 0,
  temperature: 0,
};

export default function ManualEditModal({
  projectId,
  photoId,
  onClose,
  onSaved,
}: {
  projectId: string;
  photoId: string;
  onClose: () => void;
  onSaved: (editedUrl: string) => void;
}) {
  const [values, setValues] = useState<ManualEditPayload>(ZERO);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(key: keyof ManualEditPayload) {
    return (v: number) => setValues((prev) => ({ ...prev, [key]: v / 100 }));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const res = await apiPostJson<{ edited_url: string }>(
        `/ai/projects/${projectId}/photos/${photoId}/reedit`,
        values
      );
      onSaved(res.edited_url);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar la edición manual.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="photonix-card w-full max-w-md max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-medium">Edición manual de esta foto</h3>
            <p className="text-xs text-photonix-textMuted mt-0.5">
              Solo afecta esta foto, el resto de la sesión queda igual.
            </p>
          </div>
          <button onClick={onClose} aria-label="Cerrar" className="text-photonix-textMuted hover:text-photonix-text">
            <X size={18} />
          </button>
        </div>

        <LabeledSlider label="Exposición" value={values.exposure * 100} onChange={set("exposure")} />
        <LabeledSlider label="Altas luces" value={values.highlights * 100} onChange={set("highlights")} />
        <LabeledSlider label="Sombras" value={values.shadows * 100} onChange={set("shadows")} />
        <LabeledSlider label="Blancos" value={values.whites * 100} onChange={set("whites")} />
        <LabeledSlider label="Negros" value={values.blacks * 100} onChange={set("blacks")} />
        <LabeledSlider label="Claridad" value={values.clarity * 100} min={0} max={100} onChange={set("clarity")} />
        <LabeledSlider label="Saturación" value={values.saturation * 100} onChange={set("saturation")} />
        <LabeledSlider label="Desvanecido de neblina" value={values.dehaze * 100} min={0} max={100} onChange={set("dehaze")} />
        <LabeledSlider label="Contraste" value={values.contrast * 100} onChange={set("contrast")} />
        <LabeledSlider
          label="Temperatura"
          value={values.temperature * 100}
          onChange={set("temperature")}
          formatValue={(v) => (v > 0 ? `+${v} cálido` : v < 0 ? `${v} frío` : "0")}
        />

        {error && <p className="text-sm text-photonix-danger mt-2">{error}</p>}

        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="photonix-btn-secondary text-sm flex-1" disabled={saving}>
            Cancelar
          </button>
          <button onClick={handleSave} className="photonix-btn-primary text-sm flex-1 inline-flex items-center justify-center gap-2" disabled={saving}>
            {saving && <Loader2 size={14} className="animate-spin" />}
            {saving ? "Guardando..." : "Guardar cambios"}
          </button>
        </div>
      </div>
    </div>
  );
}
