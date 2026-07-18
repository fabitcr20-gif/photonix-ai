/**
 * Política de Privacidad — Photonix AI.
 * Página pública (sin autenticación), enlazada desde el checkbox de registro.
 */
import Link from "next/link";
import Logo from "@/components/Logo";

export const metadata = {
  title: "Política de Privacidad — Photonix AI",
};

export default function PrivacidadPage() {
  return (
    <main className="min-h-screen px-4 py-12">
      <div className="w-full max-w-3xl mx-auto">
        <div className="flex justify-center mb-8">
          <Logo size="md" />
        </div>

        <div className="photonix-card">
          <h1 className="text-2xl font-semibold mb-1">Política de Privacidad</h1>
          <p className="text-sm text-photonix-textMuted mb-8">Última actualización: 17 de julio de 2026</p>

          <div className="flex flex-col gap-6 text-sm text-photonix-text leading-relaxed">
            <section>
              <p>
                Esta Política de Privacidad explica qué datos personales recolecta Photonix AI, para qué los
                usamos, con quién los compartimos y cuáles son tus derechos, de conformidad con la Ley N.° 8968 de
                Protección de la Persona frente al Tratamiento de sus Datos Personales de Costa Rica y su
                reglamento.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">1. Responsable del Tratamiento</h2>
              <p>
                <strong>Fabián Morales Barboza</strong>, persona física, cédula de identidad{" "}
                <strong>1-1480-0217</strong>, con domicilio en <strong>Curridabat, San José, Costa Rica</strong>, es
                responsable del tratamiento de los datos personales descritos en esta política. Puedes contactarnos
                en{" "}
                <a href="mailto:soporte@photonixai.cr" className="text-photonix-accent hover:underline">
                  soporte@photonixai.cr
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">2. Datos que Recolectamos</h2>
              <ul className="list-disc pl-5 flex flex-col gap-1.5">
                <li>
                  <strong>Datos de cuenta:</strong> nombre completo, correo electrónico, contraseña (almacenada de
                  forma cifrada por nuestro proveedor de autenticación, nunca en texto plano), y —si te registras
                  con Google o Apple— la información básica de perfil que esos proveedores comparten con tu
                  autorización.
                </li>
                <li>
                  <strong>Fotografías:</strong> las imágenes que subes para editar (originales, versiones
                  procesadas por la IA y versiones finales con marca de agua), así como el logo que uses como marca
                  de agua.
                </li>
                <li>
                  <strong>Datos de pago:</strong> la captura del comprobante de transferencia SINPE Móvil que
                  subes para activar tu membresía, y el plan/monto asociado.{" "}
                  <strong>No almacenamos números de tarjeta ni credenciales bancarias</strong> — el pago se realiza
                  directamente en tu aplicación bancaria, fuera de nuestra plataforma.
                </li>
                <li>
                  <strong>Datos de integraciones:</strong> si conectas tu cuenta de Google Drive, almacenamos el
                  token de autorización necesario para subir tus fotos exportadas a tu Drive, en la medida
                  necesaria para prestar esa función.
                </li>
                <li>
                  <strong>Datos técnicos:</strong> dirección IP, tipo de navegador y registros de uso del Servicio,
                  recolectados de forma automática por razones de seguridad (ej. prevención de abuso) y para
                  diagnosticar errores.
                </li>
                <li>
                  <strong>Comunicaciones:</strong> el contenido de los tickets de soporte que nos envíes.
                </li>
              </ul>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">3. Para Qué Usamos tus Datos</h2>
              <ul className="list-disc pl-5 flex flex-col gap-1">
                <li>Prestar el Servicio: procesar tus fotografías con IA y ponerlas a tu disposición.</li>
                <li>Gestionar tu cuenta, tu plan y la activación/renovación de tu membresía.</li>
                <li>Verificar manualmente tus comprobantes de pago SINPE Móvil.</li>
                <li>Enviarte recordatorios sobre el vencimiento de tu prueba gratuita o membresía.</li>
                <li>Responder a tus solicitudes de soporte.</li>
                <li>Detectar y prevenir uso fraudulento, abusivo o no autorizado del Servicio.</li>
                <li>Mejorar el Servicio y corregir errores.</li>
              </ul>
              <p className="mt-2">
                No usamos tus fotografías para entrenar modelos de inteligencia artificial de terceros, ni las
                vendemos, ni las compartimos con fines publicitarios.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">4. Fotografías de Vehículos y Datos de Terceros</h2>
              <p>
                Dado que el Servicio está orientado a fotografía automotriz, tus fotografías pueden mostrar placas
                de vehículos u otra información que podría considerarse dato personal de terceros (por ejemplo, el
                propietario del vehículo). Como fotógrafo/usuario, eres responsable de contar con la autorización
                correspondiente para fotografiar y procesar esas imágenes. Photonix AI únicamente actúa como
                encargado técnico del procesamiento de la imagen que tú decides subir.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">5. Con Quién Compartimos tus Datos</h2>
              <p className="mb-2">No vendemos tus datos personales. Los compartimos únicamente con:</p>
              <ul className="list-disc pl-5 flex flex-col gap-1">
                <li>
                  <strong>Supabase</strong> (proveedor de base de datos, autenticación y almacenamiento de
                  archivos), que actúa como encargado del tratamiento bajo sus propias medidas de seguridad.
                </li>
                <li>
                  <strong>Google</strong>, únicamente si tú decides conectar tu cuenta de Google Drive para
                  exportar tus fotos ahí, o si te registras usando Google/Apple como método de acceso.
                </li>
                <li>
                  Autoridades competentes, solo cuando exista una obligación legal que nos requiera hacerlo.
                </li>
              </ul>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">6. Almacenamiento y Seguridad</h2>
              <p>
                Tus datos se almacenan en la infraestructura de nuestro proveedor de base de datos y
                almacenamiento de archivos. Aplicamos medidas técnicas razonables para proteger tu información,
                incluyendo control de acceso basado en roles, limitación de intentos de acceso, cifrado de
                contraseñas y comunicación cifrada (HTTPS) entre tu navegador y nuestros servidores. Ningún sistema
                es 100% infalible, por lo que no podemos garantizar seguridad absoluta, pero trabajamos activamente
                para minimizar riesgos.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">7. Plazo de Conservación</h2>
              <p>
                Conservamos tus fotografías y datos de cuenta mientras tu cuenta esté activa. Puedes eliminar
                sesiones/proyectos individuales en cualquier momento desde la plataforma. Si deseas eliminar tu
                cuenta por completo y todos los datos asociados, puedes solicitarlo escribiendo a{" "}
                <a href="mailto:soporte@photonixai.cr" className="text-photonix-accent hover:underline">
                  soporte@photonixai.cr
                </a>
                . Los comprobantes de pago SINPE se conservan por el plazo necesario para efectos contables y de
                resolución de disputas conforme a la normativa aplicable.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">8. Tus Derechos (Derechos ARCO)</h2>
              <p className="mb-2">
                Conforme a la Ley N.° 8968, tienes derecho a: <strong>Acceder</strong> a tus datos personales,{" "}
                <strong>Rectificar</strong> datos inexactos, <strong>Cancelar</strong> (eliminar) tus datos, y{" "}
                <strong>Oponerte</strong> a un tratamiento específico de tus datos. También puedes revocar tu
                consentimiento en cualquier momento.
              </p>
              <p>
                Para ejercer cualquiera de estos derechos, escríbenos a{" "}
                <a href="mailto:soporte@photonixai.cr" className="text-photonix-accent hover:underline">
                  soporte@photonixai.cr
                </a>
                . Responderemos dentro de los plazos que establece la ley. También puedes presentar un reclamo ante
                la Agencia de Protección de Datos de los Habitantes (PRODHAB) de Costa Rica.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">9. Menores de Edad</h2>
              <p>
                El Servicio está dirigido a profesionales mayores de edad. No recolectamos intencionalmente datos
                de menores de edad. Si detectamos una cuenta creada por un menor sin la autorización correspondiente
                de su representante legal, la eliminaremos.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">10. Cookies y Tecnologías Similares</h2>
              <p>
                Usamos almacenamiento local del navegador (no cookies de terceros con fines publicitarios)
                principalmente para mantener tu sesión iniciada. No usamos cookies de rastreo publicitario ni las
                compartimos con redes de publicidad.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">11. Cambios a esta Política</h2>
              <p>
                Podemos actualizar esta Política ocasionalmente. Publicaremos la versión vigente en esta misma
                página con su fecha de actualización.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">12. Contacto</h2>
              <p>
                Para cualquier consulta sobre esta Política de Privacidad o el tratamiento de tus datos, escríbenos
                a{" "}
                <a href="mailto:soporte@photonixai.cr" className="text-photonix-accent hover:underline">
                  soporte@photonixai.cr
                </a>
                .
              </p>
            </section>
          </div>
        </div>

        <p className="text-center text-sm text-photonix-textMuted mt-6">
          <Link href="/register" className="text-photonix-accent hover:underline">
            Volver al registro
          </Link>
        </p>
      </div>
    </main>
  );
}
