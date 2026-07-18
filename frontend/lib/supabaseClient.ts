/**
 * Cliente de Supabase para el navegador (Auth: Google, Apple, Email/Password).
 * Usa la ANON KEY pública; toda operación sensible pasa por el backend.
 */
"use client";

import { createClient } from "@supabase/supabase-js";

// Fallback a valores de relleno (nunca reales) si las variables de entorno no
// están definidas. Sin esto, `createClient` lanza "supabaseUrl is required"
// en el momento en que este módulo se evalúa -- y como Next.js intenta
// pre-renderizar en el servidor cualquier página que lo importe (login,
// registro, todo /dashboard y /admin), un despliegue sin estas variables
// configuradas en el entorno de build (ej. Vercel) rompe el `next build`
// entero en vez de fallar solo al intentar autenticar en el navegador.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key";

if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
  // eslint-disable-next-line no-console
  console.warn(
    "NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY no están definidas. " +
      "El inicio de sesión y registro no funcionarán hasta que se configuren."
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

/** Registro con correo/contraseña. Requiere aceptar Términos y Condiciones. */
export async function signUpWithEmail(email: string, password: string, fullName: string) {
  return supabase.auth.signUp({
    email,
    password,
    options: { data: { full_name: fullName } },
  });
}

/** Inicio de sesión con correo/contraseña. */
export async function signInWithEmail(email: string, password: string) {
  return supabase.auth.signInWithPassword({ email, password });
}

/** Inicio de sesión / registro con Google OAuth. */
export async function signInWithGoogle() {
  return supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${window.location.origin}/dashboard` },
  });
}

/** Inicio de sesión / registro con Apple ID. */
export async function signInWithApple() {
  return supabase.auth.signInWithOAuth({
    provider: "apple",
    options: { redirectTo: `${window.location.origin}/dashboard` },
  });
}

export async function signOut() {
  return supabase.auth.signOut();
}

export async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
