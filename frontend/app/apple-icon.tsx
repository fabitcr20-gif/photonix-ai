/**
 * apple-touch-icon (usado por iOS al "Agregar a inicio" y por Safari).
 * iOS exige un PNG, no SVG -- se genera con `next/og` (incluido en Next.js,
 * sin dependencias nuevas) en vez de depender de una herramienta externa de
 * rasterizado que no está disponible en este entorno. Recreación simplificada
 * del isotipo para verse nítida en el tamaño pequeño de un ícono de app.
 */
import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0b0b0d",
        }}
      >
        <div
          style={{
            width: 96,
            height: 96,
            borderRadius: "50%",
            border: "7px solid #f2f2f5",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: "50%",
              background: "linear-gradient(135deg, #7c6cf6 0%, #4f8ef7 100%)",
            }}
          />
        </div>
      </div>
    ),
    { ...size }
  );
}
