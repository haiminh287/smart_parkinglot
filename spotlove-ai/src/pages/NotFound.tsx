import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Home } from "lucide-react";

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted">
      <div className="text-center">
        <h1 className="mb-2 text-6xl font-bold text-primary">404</h1>
        <h2 className="mb-2 text-2xl font-semibold text-foreground">
          Không tìm thấy trang
        </h2>
        <p className="mb-6 text-muted-foreground">
          Trang bạn đang tìm không tồn tại hoặc đã bị di chuyển.
        </p>
        <Button onClick={() => navigate("/")} className="gap-2">
          <Home className="h-4 w-4" />
          Về trang chủ
        </Button>
      </div>
    </div>
  );
};

export default NotFound;
