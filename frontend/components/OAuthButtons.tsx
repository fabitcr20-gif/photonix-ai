/**
 * Botones de inicio de sesión social: Google y Apple ID (vía Supabase Auth).
 * En login no aplica ningún requisito adicional (acceptedTerms=true por
 * defecto). En registro, el padre pasa `acceptedTerms` y `onBlocked` para
 * exigir el mismo checkbox de Términos que ya es obligatorio en el flujo por
 * correo -- antes, entrar con Google/Apple lo omitía por completo.
 */
"use client";

import { signInWithGoogle, signInWithApple } from "@/lib/supabaseClient";

export default function OAuthButtons({
  acceptedTerms = true,
  onBlocked,
}: {
  acceptedTerms?: boolean;
  onBlocked?: () => void;
}) {
  function handleGoogle() {
    if (!acceptedTerms) {
      onBlocked?.();
      return;
    }
    signInWithGoogle();
  }

  function handleApple() {
    if (!acceptedTerms) {
      onBlocked?.();
      return;
    }
    signInWithApple();
  }

  return (
    <div className="flex flex-col gap-3">
      <button onClick={handleGoogle} className="photonix-btn-secondary flex items-center justify-center gap-2">
        <svg width="18" height="18" viewBox="0 0 18 18">
          <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.88 2.7-6.62z"/>
          <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.98v2.33A9 9 0 0 0 9 18z"/>
          <path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.97H.98A9 9 0 0 0 0 9c0 1.45.35 2.83.98 4.03l2.97-2.33z"/>
          <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .98 4.97l2.97 2.33C4.66 5.17 6.65 3.58 9 3.58z"/>
        </svg>
        Continuar con Google
      </button>
      <button onClick={handleApple} className="photonix-btn-secondary flex items-center justify-center gap-2">
        <svg width="16" height="18" viewBox="0 0 16 18" fill="currentColor">
          <path d="M13.14 9.55c-.02-2.02 1.65-2.99 1.72-3.04-.94-1.37-2.4-1.56-2.92-1.58-1.24-.13-2.43.73-3.06.73-.63 0-1.6-.71-2.63-.69-1.35.02-2.6.79-3.29 2C1.5 8.9 2.4 12.4 3.75 14.31c.66.94 1.44 1.99 2.47 1.95 1-.04 1.37-.64 2.58-.64s1.55.64 2.6.62c1.08-.02 1.75-.98 2.4-1.93.76-1.1 1.07-2.17 1.09-2.22-.02-.01-2.08-.8-2.75-3.54zM11.1 3.6c.54-.66.91-1.57.81-2.48-.78.03-1.74.52-2.3 1.17-.5.58-.94 1.51-.82 2.4.87.07 1.76-.44 2.31-1.09z"/>
        </svg>
        Continuar con Apple
      </button>
    </div>
  );
}
