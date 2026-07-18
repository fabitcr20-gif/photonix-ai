/**
 * Términos y Condiciones — Photonix AI.
 * Página pública (sin autenticación), enlazada desde el checkbox de registro.
 */
import Link from "next/link";
import Logo from "@/components/Logo";

export const metadata = {
  title: "Términos y Condiciones — Photonix AI",
};

export default function TerminosPage() {
  return (
    <main className="min-h-screen px-4 py-12">
      <div className="w-full max-w-3xl mx-auto">
        <div className="flex justify-center mb-8">
          <Logo size="md" />
        </div>

        <div className="photonix-card">
          <h1 className="text-2xl font-semibold mb-1">Términos y Condiciones</h1>
          <p className="text-sm text-photonix-textMuted mb-8">Última actualización: 17 de julio de 2026</p>

          <div className="flex flex-col gap-6 text-sm text-photonix-text leading-relaxed">
            <section>
              <h2 className="text-base font-medium mb-2">1. Aceptación de los Términos</h2>
              <p>
                Estos Términos y Condiciones ("Términos") regulan el uso de Photonix AI (el "Servicio"),
                una plataforma de edición fotográfica automatizada con inteligencia artificial operada por{" "}
                <strong>Fabián Morales Barboza</strong>, persona física, cédula de identidad{" "}
                <strong>1-1480-0217</strong>, con domicilio en <strong>Curridabat, San José, Costa Rica</strong>{" "}
                ("nosotros", "Photonix AI"). Al crear una cuenta o usar el Servicio, aceptas estos Términos en su
                totalidad. Si no estás de acuerdo, no debes usar el Servicio.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">2. Descripción del Servicio</h2>
              <p>
                Photonix AI permite a fotógrafos y diseñadores profesionales cargar fotografías (individualmente o
                por lote) para que sean editadas automáticamente mediante inteligencia artificial: corrección de
                perspectiva, ajustes de exposición/color/nitidez, reducción de ruido, y —según el plan
                contratado— eliminación de elementos como placas de vehículos, logos, postes y cables. El
                resultado puede exportarse con marca de agua personalizada, en archivo ZIP o mediante integración
                con Google Drive.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">3. Registro y Cuenta de Usuario</h2>
              <p className="mb-2">
                Para usar el Servicio debes crear una cuenta con tu correo electrónico y contraseña, o mediante tu
                cuenta de Google o Apple. Eres responsable de mantener la confidencialidad de tus credenciales y de
                toda actividad que ocurra bajo tu cuenta. Debes ser mayor de edad (18 años) o contar con el
                consentimiento de tu representante legal para usar el Servicio, y proporcionar información
                verdadera y actualizada al registrarte.
              </p>
              <p>
                Nos reservamos el derecho de suspender o bloquear cualquier cuenta que incumpla estos Términos, que
                incurra en mora de pago, o que muestre indicios de actividad fraudulenta o abusiva, sin necesidad
                de aviso previo cuando la situación lo amerite.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">4. Planes, Precios y Forma de Pago</h2>
              <p className="mb-2">
                Ofrecemos los planes Starter, Pro y Studio, cada uno con precio y límites propios (cantidad de
                fotos por carga, eliminación de objetos, prioridad de procesamiento, entre otros) publicados en la
                sección "Mi Membresía" de la plataforma. Los precios están expresados en colones costarricenses
                (₡) e incluyen los tributos aplicables, salvo que se indique lo contrario.
              </p>
              <p className="mb-2">
                El único método de pago disponible actualmente es <strong>SINPE Móvil</strong>. Para activar o
                renovar un plan, debes realizar la transferencia al número indicado en la plataforma y subir una
                captura del comprobante. La activación de tu membresía <strong>no es automática</strong>: un
                administrador revisa manualmente cada comprobante y puede aprobarlo o rechazarlo (por ejemplo, si
                el monto no coincide o el comprobante no es legible). Mientras tu comprobante esté pendiente de
                revisión, tu cuenta permanece en tu plan/estado anterior.
              </p>
              <p>
                Las membresías tienen una vigencia de 30 días desde su aprobación y no se renuevan
                automáticamente: debes subir un nuevo comprobante antes de que venza para mantener el acceso sin
                interrupciones. Dado que la verificación de pago es manual y no reversible una vez aprobada, los
                pagos realizados por SINPE Móvil <strong>no son reembolsables</strong>, salvo error atribuible
                directamente a Photonix AI (ej. cobro duplicado).
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">5. Prueba Gratuita</h2>
              <p>
                Las cuentas nuevas reciben 30 días de prueba gratuita con acceso a las funciones básicas del
                Servicio, sin necesidad de método de pago. Al vencer el período de prueba sin una membresía activa,
                el acceso a las funciones de edición y exportación se restringe hasta que actives un plan pagado.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">6. Tus Fotografías</h2>
              <p className="mb-2">
                Las fotografías que subes al Servicio (originales, editadas y finales) siguen siendo{" "}
                <strong>tuyas</strong>. No reclamamos propiedad sobre tu contenido. Al subir una fotografía, nos
                otorgas una licencia limitada, no exclusiva y revocable para almacenarla, procesarla con nuestro
                motor de edición y ponerla a tu disposición para descarga/exportación — únicamente con el fin de
                prestarte el Servicio.
              </p>
              <p className="mb-2">
                Declaras que tienes los derechos necesarios sobre cada fotografía que subes (por ejemplo, que eres
                el fotógrafo o cuentas con autorización del titular de los derechos) y que su contenido no infringe
                derechos de terceros ni leyes aplicables. No debes subir contenido ilegal, que viole derechos de
                autor de terceros, o que contenga datos personales de personas que no hayan autorizado su
                fotografía cuando la ley lo exija.
              </p>
              <p>
                El motor de eliminación de objetos (placas, logos, postes, cables) es una herramienta automatizada
                de asistencia y puede no ser perfecta en todos los casos; eres responsable de revisar el resultado
                final antes de entregarlo a tus propios clientes.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">7. Marca de Agua y Exportación</h2>
              <p>
                Puedes configurar tu propio logo como marca de agua para tus fotos editadas. Eres responsable de
                que el logo que subas no infrinja derechos de terceros. La integración con Google Drive requiere
                que autorices el acceso a tu propia cuenta de Google mediante OAuth; puedes revocar ese acceso en
                cualquier momento desde la configuración de tu cuenta de Google.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">8. Uso Aceptable</h2>
              <p className="mb-2">Al usar el Servicio, te comprometes a NO:</p>
              <ul className="list-disc pl-5 flex flex-col gap-1">
                <li>Subir contenido ilegal, difamatorio, o que infrinja derechos de propiedad intelectual de terceros.</li>
                <li>Intentar vulnerar, sobrecargar o interferir con la seguridad o el funcionamiento del Servicio.</li>
                <li>Acceder o intentar acceder a cuentas, datos o fotografías de otros usuarios sin autorización.</li>
                <li>Usar el Servicio para procesar volúmenes o patrones de solicitudes característicos de bots o automatización no autorizada.</li>
                <li>Revender o redistribuir el acceso al Servicio sin autorización expresa por escrito.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">9. Propiedad Intelectual de Photonix AI</h2>
              <p>
                El software, la marca, el diseño de la plataforma, los algoritmos de edición y demás elementos del
                Servicio (excluyendo tu contenido) son propiedad de Photonix AI o de sus licenciantes y están
                protegidos por las leyes de propiedad intelectual aplicables. Estos Términos no te otorgan ningún
                derecho sobre ellos más allá del uso del Servicio conforme a lo aquí descrito.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">10. Disponibilidad del Servicio</h2>
              <p>
                Trabajamos para mantener el Servicio disponible de forma continua, pero no garantizamos que
                funcione sin interrupciones, errores o demoras. El Servicio se ofrece "tal cual" y en mejora
                continua; podemos realizar mantenimientos, actualizaciones o cambios en las funciones disponibles
                en cualquier momento.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">11. Limitación de Responsabilidad</h2>
              <p>
                En la medida permitida por la ley, Photonix AI no será responsable por daños indirectos,
                incidentales o consecuentes derivados del uso o la imposibilidad de uso del Servicio, incluyendo
                pérdida de ingresos o de oportunidades comerciales. Nada en estos Términos limita responsabilidad
                que no pueda excluirse conforme a la legislación costarricense (por ejemplo, en casos de dolo o
                culpa grave).
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">12. Cancelación y Terminación</h2>
              <p>
                Puedes dejar de usar el Servicio en cualquier momento simplemente no renovando tu membresía.
                Podemos suspender o cancelar tu cuenta si incumples estos Términos, incurres en mora prolongada, o
                usas el Servicio de forma fraudulenta o abusiva. Al día de hoy, la eliminación completa de una
                cuenta y sus datos asociados debe solicitarse por escrito a través de nuestro canal de soporte.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">13. Modificaciones a estos Términos</h2>
              <p>
                Podemos actualizar estos Términos ocasionalmente. Publicaremos la versión vigente en esta misma
                página con su fecha de actualización. El uso continuado del Servicio después de una actualización
                implica tu aceptación de los nuevos Términos.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">14. Ley Aplicable</h2>
              <p>
                Estos Términos se rigen por las leyes de la República de Costa Rica. Cualquier controversia se
                someterá a los tribunales competentes de Costa Rica.
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium mb-2">15. Contacto</h2>
              <p>
                Para consultas sobre estos Términos, escríbenos a{" "}
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
