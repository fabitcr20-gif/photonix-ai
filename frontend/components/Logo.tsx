/** Componente reutilizable del logo de Photonix AI. */
import Image from "next/image";

export default function Logo({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const heights = { sm: 28, md: 40, lg: 64 };
  const h = heights[size];
  return (
    <Image
      src="/logo.svg"
      alt="Photonix AI"
      width={h * 4.7}
      height={h}
      priority
      style={{ height: h, width: "auto" }}
    />
  );
}
