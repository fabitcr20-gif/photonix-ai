import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Photonix AI",
    short_name: "Photonix AI",
    description:
      "Edición fotográfica automatizada con Inteligencia Artificial para fotógrafos y diseñadores profesionales.",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#0b0b0d",
    theme_color: "#0b0b0d",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
      { src: "/apple-icon.png", sizes: "180x180", type: "image/png" },
    ],
  };
}
