import AdminSidebar from "@/components/AdminSidebar";
import AuthGate from "@/components/AuthGate";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate requireAdmin>
      <div className="flex min-h-screen bg-photonix-bg">
        <AdminSidebar />
        <div className="flex-1 p-8">{children}</div>
      </div>
    </AuthGate>
  );
}
