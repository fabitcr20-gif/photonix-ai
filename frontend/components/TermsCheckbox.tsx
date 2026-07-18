/** Checkbox obligatorio de Términos y Condiciones, requerido para registrarse. */
"use client";

export default function TermsCheckbox({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-2.5 text-sm text-photonix-textMuted cursor-pointer select-none">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        required
        className="mt-0.5 accent-photonix-accent w-4 h-4"
      />
      <span>
        Acepto los{" "}
        <a href="/terminos" target="_blank" rel="noopener noreferrer" className="text-photonix-accent hover:underline">
          Términos y Condiciones
        </a>{" "}
        y la{" "}
        <a href="/privacidad" target="_blank" rel="noopener noreferrer" className="text-photonix-accent hover:underline">
          Política de Privacidad
        </a>{" "}
        de Photonix AI.
      </span>
    </label>
  );
}
