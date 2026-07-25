# Esquema de base de datos (Supabase / Postgres)

Photonix AI no usa un framework de migraciones (Alembic, etc.) -- los
cambios de esquema se corren manualmente en el SQL Editor de Supabase, igual
que siempre. Lo que cambia a partir de ahora es que ese SQL queda **versionado
en el repo** en vez de perderse después de correrlo una vez.

## Cómo usar esto

- **`schema.sql`**: el esquema completo tal como debería estar HOY en
  producción (reconstruido a partir del uso real del código, no de una
  documentación que se había quedado desactualizada). Sirve para levantar un
  ambiente nuevo desde cero (staging, recuperación ante desastre): correr
  este archivo completo primero.
- **`migrations/`**: cada cambio de esquema NUEVO a partir de ahora va en un
  archivo propio aquí, numerado en orden (`0001_descripcion.sql`,
  `0002_descripcion.sql`, ...). Nunca se edita `schema.sql` directamente para
  reflejar un cambio nuevo -- se agrega un archivo de migración, y
  `schema.sql` se actualiza aparte para que siga reflejando el estado final
  (así alguien reconstruyendo desde cero no tiene que aplicar 40 migraciones
  a mano, pero el historial real de cómo se llegó ahí queda en git).

## Al aplicar un cambio

1. Escribir el SQL en un archivo nuevo dentro de `migrations/`.
2. Correrlo en el SQL Editor de Supabase (producción).
3. Reflejar el mismo cambio en `schema.sql` para que el "estado final" del
   archivo base siga siendo el real.
4. Commitear ambos cambios juntos.
