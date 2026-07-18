/** Slider premium con etiqueta y valor, usado en Opciones Avanzadas. */
"use client";

export default function LabeledSlider({
  label,
  value,
  onChange,
  min = -100,
  max = 100,
  formatValue,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  formatValue?: (value: number) => string;
}) {
  return (
    <div className="mb-4 last:mb-0">
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-xs text-photonix-textMuted">{label}</label>
        <span className="text-xs text-photonix-text tabular-nums">
          {formatValue ? formatValue(value) : value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="photonix-slider"
        aria-label={label}
      />
    </div>
  );
}
