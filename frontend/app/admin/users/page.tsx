/**
 * Panel de administrador: todos los clientes con su plan/estado vigente,
 * para autorizar acceso o bloquear por mora sin depender de que exista un
 * comprobante SINPE pendiente (ej. alguien cuya membresía ya venció y no ha
 * vuelto a pagar).
 */
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPostJson } from "@/lib/api";
import type { AdminUser } from "@/types";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function loadUsers() {
    setLoading(true);
    const data = await apiGet<AdminUser[]>("/admin/users");
    setUsers(data);
    setLoading(false);
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function toggleBlock(user: AdminUser) {
    if (!user.is_blocked && !confirm(`¿Bloquear a ${user.email}? Perderá acceso de inmediato.`)) return;
    setBusyId(user.user_id);
    try {
      await apiPostJson(`/admin/users/${user.user_id}/${user.is_blocked ? "unblock" : "block"}`, {});
      setUsers((prev) =>
        prev.map((u) => (u.user_id === user.user_id ? { ...u, is_blocked: !user.is_blocked } : u))
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Usuarios</h1>
      <p className="text-photonix-textMuted mb-6">
        Todos los clientes registrados, con su plan vigente. Bloquea el acceso de inmediato en caso de
        mora o abuso, sin esperar a que venza la membresía.
      </p>

      {loading && <p className="text-photonix-textMuted">Cargando...</p>}

      {!loading && users.length === 0 && (
        <div className="photonix-card text-center text-photonix-textMuted">Todavía no hay clientes registrados.</div>
      )}

      {!loading && users.length > 0 && (
        <div className="photonix-card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-photonix-textMuted border-b border-photonix-border">
                <th className="py-3 px-4 font-medium">Cliente</th>
                <th className="py-3 px-4 font-medium">Plan</th>
                <th className="py-3 px-4 font-medium">Vence</th>
                <th className="py-3 px-4 font-medium">Estado</th>
                <th className="py-3 px-4 font-medium text-right">Acción</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.user_id} className="border-b border-photonix-border last:border-0">
                  <td className="py-3 px-4">
                    <p className="font-medium">{u.full_name ?? u.email}</p>
                    <p className="text-xs text-photonix-textMuted">{u.email}</p>
                  </td>
                  <td className="py-3 px-4 capitalize">{u.plan}</td>
                  <td className="py-3 px-4 text-photonix-textMuted">
                    {u.ends_at ? new Date(u.ends_at).toLocaleDateString("es-CR") : "—"}
                  </td>
                  <td className="py-3 px-4">
                    {u.is_blocked ? (
                      <span className="text-xs px-2 py-1 rounded-full bg-photonix-danger/10 text-photonix-danger border border-photonix-danger/40">
                        Bloqueado
                      </span>
                    ) : u.active ? (
                      <span className="text-xs px-2 py-1 rounded-full bg-photonix-accent/10 text-photonix-accent border border-photonix-accent/30">
                        Activo
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-1 rounded-full bg-white/[0.04] text-photonix-textMuted">
                        Vencido
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => toggleBlock(u)}
                      disabled={busyId === u.user_id}
                      className={
                        u.is_blocked
                          ? "photonix-btn-secondary text-xs px-3 py-1.5"
                          : "bg-photonix-danger/10 text-photonix-danger border border-photonix-danger/40 rounded-lg font-medium px-3 py-1.5 hover:bg-photonix-danger/20 transition-colors text-xs"
                      }
                    >
                      {u.is_blocked ? "Desbloquear" : "Bloquear"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
