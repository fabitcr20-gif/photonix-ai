/**
 * Landing page de Photonix AI: explica qué es la plataforma, sus ventajas
 * frente a editores tradicionales, los planes disponibles (en colones, vía
 * SINPE Móvil) y da acceso a inicio de sesión / registro.
 *
 * Los precios y funciones de cada plan deben reflejar siempre el catálogo
 * real del backend: ver backend/app/models/membership.py (PLAN_CATALOG) y
 * backend/app/core/plans.py (PLAN_FEATURES).
 */
import Link from "next/link";
import { Check, Clock, Sparkles, Wand2, Layers, ShieldCheck, Upload, Palette, Cpu, Download, Camera, Star } from "lucide-react";
import Logo from "@/components/Logo";
import Accordion from "@/components/Accordion";

const HOW_IT_WORKS = [
  { icon: Upload, title: "1. Cargas tu sesión", description: "Sube una foto o una carpeta completa — cientos o miles de imágenes en un solo paso." },
  { icon: Palette, title: "2. Eliges el estilo", description: "Selecciona un perfil de estilo IA (bodas, automotriz, retrato...) o deja que la IA decida por ti." },
  { icon: Cpu, title: "3. La IA procesa", description: "Ajustes de luz y color, limpieza, corrección de perspectiva y eliminación de objetos, automáticos." },
  { icon: Download, title: "4. Exportas", description: "Revisa el antes/después, ajusta si quieres una foto puntual, y descarga en ZIP o a Google Drive." },
];

const USE_CASES = [
  { title: "Bodas y eventos", description: "Sesiones de cientos o miles de fotos editadas en lote con un mismo estilo consistente." },
  { title: "Fotografía automotriz", description: "Elimina placas, postes y cables automáticamente — el caso de uso donde Photonix AI rinde más." },
  { title: "Inmobiliaria", description: "Corrección de perspectiva y limpieza automática para fotos de propiedades." },
  { title: "Retrato", description: "Ajustes de tono y exposición en lote para sesiones completas." },
  { title: "Eventos corporativos", description: "Procesa sesiones grandes con marca de agua de tu estudio en cada foto." },
];

const FAQS = [
  {
    q: "¿Puedo cancelar cuando quiera?",
    a: "Sí. Tu membresía dura 30 días y no se renueva automáticamente — simplemente no subes un nuevo comprobante si decides no continuar.",
  },
  {
    q: "¿Qué tan seguras están mis fotos?",
    a: "Tus fotografías siguen siendo tuyas. Se almacenan para prestarte el servicio (procesarlas y ponerlas a tu disposición) y no se usan para entrenar modelos de terceros ni se comparten con fines publicitarios. Más detalle en nuestra Política de Privacidad.",
  },
  {
    q: "¿Cuánto tarda en aprobarse mi pago por SINPE Móvil?",
    a: "Aprobamos tu comprobante en menos de 24 horas hábiles. Mientras esté pendiente, tu cuenta mantiene tu plan/estado anterior.",
  },
  {
    q: "¿Qué pasa si rechazan mi comprobante?",
    a: "Te avisamos por correo con el motivo (por ejemplo, monto que no coincide o imagen no legible) y puedes subir uno nuevo desde tu panel, en \"Mi Membresía\".",
  },
];

const ADVANTAGES = [
  {
    icon: Clock,
    title: "Horas de edición en minutos",
    description:
      "Mientras en Lightroom o Capture One editas foto por foto, Photonix AI procesa sesiones completas de miles de fotografías en un solo lote: ajustes, limpieza y corrección de perspectiva automáticos.",
  },
  {
    icon: Wand2,
    title: "Aprende tu estilo, no lo reemplaza",
    description:
      "A diferencia de los presets genéricos de otras apps, Photonix AI puede entrenarse con tus propias fotos editadas para reproducir tu identidad visual, no un look estándar.",
  },
  {
    icon: Layers,
    title: "Elimina lo que otros dejan pasar",
    description:
      "Placas de autos, postes de luz y cables eléctricos se detectan y eliminan automáticamente — algo que en Photoshop implica horas de retoque manual foto por foto.",
  },
  {
    icon: Sparkles,
    title: "Pensado para volumen real",
    description:
      "Diseñado para procesar sesiones de 500, 1.000 o más fotografías sin perder rendimiento, con carga masiva de carpetas completas en un solo paso.",
  },
  {
    icon: ShieldCheck,
    title: "Sin curva de aprendizaje",
    description:
      "Nada de paneles complejos ni docenas de deslizadores: eliges tu sesión, activas las opciones de IA que quieres y Photonix AI hace el resto.",
  },
  {
    icon: Check,
    title: "Precios pensados para Costa Rica",
    description:
      "Planes en colones y pago simple por SINPE Móvil, sin tarjetas internacionales ni suscripciones en dólares como los editores tradicionales.",
  },
];

const PLANS = [
  {
    id: "trial",
    name: "Prueba Gratuita",
    price: "₡0",
    period: "por 30 días",
    highlight: false,
    features: [
      "Acceso completo por 1 mes",
      "Ajustes automáticos + limpieza de imagen",
      "Eliminación de objetos (placas, postes, cables)",
      "Marca de agua personalizada",
      "Hasta 100 fotos por carga masiva",
    ],
    cta: { label: "Empieza gratis", href: "/register" },
  },
  {
    id: "starter",
    name: "Photonix Starter",
    price: "₡3.500",
    period: "/ mes",
    highlight: false,
    features: [
      "Ajustes automáticos + limpieza de imagen",
      "Marca de agua (posición única)",
      "Hasta 100 fotos por carga masiva",
      "Corrección de perspectiva",
    ],
    cta: { label: "Elegir Starter", href: "/register" },
  },
  {
    id: "pro",
    name: "Photonix Pro",
    price: "₡7.000",
    period: "/ mes",
    highlight: true,
    features: [
      "Todo lo de Starter",
      "Eliminación de objetos (placas, postes, cables)",
      "Marca de agua con múltiples plantillas",
      "Hasta 500 fotos por carga masiva",
    ],
    cta: { label: "Elegir Pro", href: "/register" },
  },
  {
    id: "studio",
    name: "Photonix Studio",
    price: "₡12.000",
    period: "/ mes",
    highlight: false,
    features: [
      "Todo lo de Pro",
      "Fotos por carga masiva ilimitadas",
      "Procesamiento con prioridad",
      "Ideal para estudios con varios fotógrafos",
    ],
    cta: { label: "Elegir Studio", href: "/register" },
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen">
      {/* Barra de navegación */}
      <header className="flex items-center justify-between px-6 sm:px-10 py-5 border-b border-photonix-border">
        <Logo size="sm" />
        <div className="flex items-center gap-3">
          <Link href="/login" className="photonix-btn-secondary">
            Iniciar sesión
          </Link>
          <Link href="/register" className="photonix-btn-primary">
            Registrarse
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="flex flex-col items-center justify-center text-center gap-6 px-4 py-20">
        <div className="max-w-2xl">
          <h1 className="text-3xl sm:text-4xl font-semibold mb-4">
            Edición fotográfica masiva, potenciada por IA
          </h1>
          <p className="text-photonix-textMuted text-lg">
            Photonix AI automatiza la edición de tus sesiones completas — ajustes,
            limpieza, corrección de perspectiva, eliminación de elementos y marca
            de agua — para que dediques tu tiempo a lo que importa: hacer sesiones
            y conseguir más clientes.
          </p>
        </div>
        <div className="flex gap-3">
          <Link href="/register" className="photonix-btn-primary">
            Empieza gratis por 30 días
          </Link>
          <Link href="/login" className="photonix-btn-secondary">
            Iniciar sesión
          </Link>
        </div>
      </section>

      {/* Qué es Photonix AI */}
      <section className="max-w-3xl mx-auto px-4 py-16 text-center">
        <h2 className="text-2xl font-semibold mb-4">¿Qué es Photonix AI?</h2>
        <p className="text-photonix-textMuted">
          Photonix AI es una plataforma de edición fotográfica automatizada
          diseñada para fotógrafos y diseñadores gráficos profesionales que
          manejan sesiones de cientos o miles de fotografías. En lugar de
          editar imagen por imagen, cargas una sesión completa (individual o
          por carpeta) y un motor de inteligencia artificial analiza cada
          foto — hora del día, clima, luz, ángulo y encuadre — para aplicar
          automáticamente ajustes de luces, sombras, tono, saturación,
          limpieza de ruido y polvo, corrección de perspectiva, eliminación de
          objetos no deseados y tu propia marca de agua. El resultado: menos
          clics, menos horas frente a la pantalla, y más tiempo para hacer
          sesiones y atender clientes.
        </p>
      </section>

      {/* Cómo funciona */}
      <section className="max-w-5xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-semibold text-center mb-10">Cómo funciona</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {HOW_IT_WORKS.map(({ icon: Icon, title, description }) => (
            <div key={title} className="photonix-card">
              <Icon className="text-photonix-accent mb-3" size={24} />
              <h3 className="font-medium mb-2 text-sm">{title}</h3>
              <p className="text-sm text-photonix-textMuted">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Ventajas frente a otros editores */}
      <section className="bg-photonix-surface/40 py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-semibold text-center mb-2">
            ¿Por qué Photonix AI y no otro editor?
          </h2>
          <p className="text-photonix-textMuted text-center mb-10">
            Lightroom, Photoshop y Capture One son excelentes herramientas
            manuales. Photonix AI está diseñado para automatizar lo que en
            esas apps te toma editar a mano, foto por foto.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {ADVANTAGES.map(({ icon: Icon, title, description }) => (
              <div key={title} className="photonix-card">
                <Icon className="text-photonix-accent mb-3" size={28} />
                <h3 className="font-medium mb-2">{title}</h3>
                <p className="text-sm text-photonix-textMuted">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Casos de uso */}
      <section className="max-w-5xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-semibold text-center mb-2">Casos de uso</h2>
        <p className="text-photonix-textMuted text-center mb-10">
          Pensado para sesiones de volumen real, en distintos tipos de fotografía profesional.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {USE_CASES.map(({ title, description }) => (
            <div key={title} className="photonix-card">
              <h3 className="font-medium mb-2">{title}</h3>
              <p className="text-sm text-photonix-textMuted">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Antes / Después */}
      <section className="bg-photonix-surface/40 py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl font-semibold mb-2">Antes / Después</h2>
          <p className="text-photonix-textMuted mb-8">
            Ejemplos reales de sesiones editadas con Photonix AI.
          </p>
          <div className="photonix-card border-dashed">
            <p className="text-sm text-photonix-textMuted">
              Estamos preparando ejemplos reales de fotos editadas con autorización de nuestros
              primeros fotógrafos Early Access. Vuelve pronto para verlos aquí.
            </p>
          </div>
        </div>
      </section>

      {/* Capturas del editor */}
      <section className="max-w-5xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-semibold text-center mb-2">Así se ve por dentro</h2>
        <p className="text-photonix-textMuted text-center mb-10">
          Capturas reales de la interfaz de Photonix AI.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {["Carga y estilo IA", "Procesamiento con IA", "Antes / Después y exportación"].map((caption) => (
            <div key={caption} className="photonix-card p-0 overflow-hidden">
              <div className="aspect-video bg-photonix-surfaceAlt flex items-center justify-center">
                <Camera className="text-photonix-textMuted" size={28} />
              </div>
              <p className="text-sm text-photonix-textMuted p-4">{caption}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Prueba social */}
      <section className="bg-photonix-surface/40 py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-semibold text-center mb-2">Lo que dicen los fotógrafos</h2>
          <p className="text-photonix-textMuted text-center mb-10">
            Photonix AI está en Early Access — estas son las primeras opiniones que vamos a compartir aquí.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {[1, 2, 3].map((n) => (
              <div key={n} className="photonix-card text-center">
                <div className="flex justify-center gap-0.5 mb-3">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Star key={s} size={14} className="text-photonix-border" />
                  ))}
                </div>
                <p className="text-sm text-photonix-textMuted">
                  Sé de los primeros fotógrafos en compartir tu experiencia con Photonix AI.
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Planes */}
      <section className="max-w-6xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-semibold text-center mb-2">Planes y precios</h2>
        <p className="text-photonix-textMuted text-center mb-10">
          Precios en colones costarricenses (₡), pago simple por SINPE Móvil:
          subes tu comprobante y tu membresía se activa en cuanto un
          administrador lo aprueba.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`photonix-card flex flex-col ${
                plan.highlight ? "border-photonix-accent border-2" : ""
              }`}
            >
              {plan.highlight && (
                <span className="text-xs font-medium text-photonix-accent mb-2">
                  MÁS POPULAR
                </span>
              )}
              <h3 className="font-medium">{plan.name}</h3>
              <p className="mt-2 mb-4">
                <span className="text-2xl font-semibold">{plan.price}</span>{" "}
                <span className="text-sm text-photonix-textMuted">{plan.period}</span>
              </p>
              <ul className="flex-1 flex flex-col gap-2 text-sm text-photonix-textMuted mb-6">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <Check size={16} className="text-photonix-accent shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href={plan.cta.href}
                className={plan.highlight ? "photonix-btn-primary text-center" : "photonix-btn-secondary text-center"}
              >
                {plan.cta.label}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="max-w-2xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-semibold text-center mb-10">Preguntas frecuentes</h2>
        <div className="flex flex-col gap-3">
          {FAQS.map(({ q, a }) => (
            <Accordion key={q} title={q}>
              <p className="text-sm text-photonix-textMuted">{a}</p>
            </Accordion>
          ))}
        </div>
      </section>

      {/* CTA final */}
      <section className="text-center px-4 py-20 border-t border-photonix-border">
        <h2 className="text-2xl font-semibold mb-4">
          Recupera horas en cada sesión fotográfica
        </h2>
        <p className="text-photonix-textMuted max-w-xl mx-auto mb-6">
          Regístrate hoy y prueba Photonix AI gratis durante 30 días, con
          acceso completo a todas las funciones.
        </p>
        <Link href="/register" className="photonix-btn-primary">
          Crear cuenta gratis
        </Link>
      </section>

      <footer className="text-center text-xs text-photonix-textMuted py-8 border-t border-photonix-border">
        <div className="flex justify-center gap-4 mb-3">
          <Link href="/terminos" className="hover:text-photonix-text hover:underline">
            Términos y Condiciones
          </Link>
          <Link href="/privacidad" className="hover:text-photonix-text hover:underline">
            Política de Privacidad
          </Link>
          <a href="mailto:soporte@photonixai.cr" className="hover:text-photonix-text hover:underline">
            soporte@photonixai.cr
          </a>
        </div>
        © {new Date().getFullYear()} Photonix AI. Todos los derechos reservados.
      </footer>
    </main>
  );
}
