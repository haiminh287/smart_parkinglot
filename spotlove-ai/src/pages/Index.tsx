import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/use-auth";
import UserDashboard from "./UserDashboard";

export default function Index() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect admin to admin dashboard
    if (!isLoading && user?.role === "admin") {
      navigate("/admin/dashboard", { replace: true });
    }
  }, [user, isLoading, navigate]);

  // Show loading while checking auth
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        Loading...
      </div>
    );
  }

  // Render user dashboard (admins already redirected)
  return <UserDashboard />;
}
