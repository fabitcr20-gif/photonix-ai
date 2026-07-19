/**
 * Cliente HTTP hacia el backend de Photonix AI (FastAPI).
 * Adjunta automáticamente el JWT de Supabase en cada request autenticado.
 */
import { getAccessToken } from "./supabaseClient";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

async function authHeaders(): Promise<HeadersInit> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * FastAPI devuelve errores como JSON `{"detail": "mensaje legible"}` (o, en
 * errores de validación de Pydantic, `{"detail": [{"msg": "...", ...}, ...]}`).
 * Antes se usaba `res.text()` crudo como mensaje de error en TODA la app, así
 * que cualquier error del backend se mostraba como el JSON completo sin
 * parsear (ej. `{"detail":"Formato no soportado..."}`) en vez del mensaje.
 * Esta función intenta extraer solo el texto legible; si el cuerpo no es el
 * JSON esperado, cae de vuelta al texto crudo.
 */
function parseErrorDetail(text: string, status: number): string {
  try {
    const parsed = JSON.parse(text);
    const detail = parsed?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => d?.msg || JSON.stringify(d)).join(", ");
    }
  } catch {
    // el cuerpo no era JSON (ej. error HTML de un proxy/gateway) -- se usa el texto crudo abajo
  }
  return text || `Error ${status}`;
}

async function errorMessageFrom(res: Response): Promise<string> {
  return parseErrorDetail(await res.text(), res.status);
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(await errorMessageFrom(res));
  return res.json();
}

export async function apiPostJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorMessageFrom(res));
  return res.json();
}

export async function apiPatchJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorMessageFrom(res));
  return res.json();
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(await errorMessageFrom(res));
  return res.json();
}

export async function apiPostForm<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: await authHeaders(), // NO Content-Type: el navegador arma el boundary del multipart
    body: formData,
  });
  if (!res.ok) throw new Error(await errorMessageFrom(res));
  return res.json();
}

/**
 * Igual que apiPostForm, pero reporta el progreso real de la subida
 * (0-100) a través de onProgress. `fetch` no expone progreso de subida en
 * todos los navegadores, así que aquí se usa XMLHttpRequest.
 */
export async function apiPostFormWithProgress<T>(
  path: string,
  formData: FormData,
  onProgress?: (percent: number) => void
): Promise<T> {
  const headers = await authHeaders();
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}${path}`);
    Object.entries(headers).forEach(([key, value]) => xhr.setRequestHeader(key, value as string));

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(parseErrorDetail(xhr.responseText, xhr.status)));
      }
    };
    xhr.onerror = () => reject(new Error("Error de red al subir los archivos."));

    xhr.send(formData);
  });
}

/** Descarga un archivo protegido (requiere el token de auth) y dispara la
 * descarga en el navegador, extrayendo el nombre de archivo del header
 * Content-Disposition que devuelve el backend. */
export async function apiDownloadFile(path: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}${path}`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(await res.text());

  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : "descarga";

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
