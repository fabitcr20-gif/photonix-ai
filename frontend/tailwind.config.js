/**
 * Configuración de Tailwind CSS — Tema oscuro premium de Photonix AI.
 * Paleta refinada para sentirse a la altura de productos como Linear, Vercel
 * o Arc: negro casi puro de fondo, paneles y tarjetas apenas más claros,
 * bordes muy sutiles, y un acento en degradado morado-azul para los estados
 * activos/interactivos. Los NOMBRES de los tokens se mantienen (para no
 * romper ninguna clase ya usada en el resto del proyecto) — solo se
 * refrescaron los valores.
 */
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        photonix: {
          bg: "#0b0b0d",         // fondo principal
          surface: "#141418",    // paneles
          surfaceAlt: "#1a1a22", // tarjetas (ligeramente más elevadas)
          border: "#242429",     // bordes muy sutiles
          navy: "#0e0e12",       // fondo profundo alterno (ej. sidebar admin)
          steel: "#8b8b9a",      // acento secundario frío
          accent: "#7c6cf6",     // morado (inicio del degradado de acción)
          accent2: "#4f8ef7",    // azul (fin del degradado de acción)
          success: "#3ecf8e",
          warning: "#f5a623",
          danger: "#f0554b",
          text: "#f2f2f5",
          textMuted: "#8b8b93",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "photonix-gradient": "linear-gradient(90deg, #7c6cf6 0%, #4f8ef7 100%)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      letterSpacing: {
        tightish: "-0.01em",
      },
    },
  },
  plugins: [],
};
