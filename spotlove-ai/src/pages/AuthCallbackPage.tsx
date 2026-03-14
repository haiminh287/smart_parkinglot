import { useEffect, useMemo, useState } from "react";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAppDispatch } from "@/store/hooks";
import { fetchCurrentUser } from "@/store/slices/authSlice";

const DEFAULT_REDIRECT_PATH = "/";

function sanitizeReturnTo(value: string | null): string {
  if (!value) {
    return DEFAULT_REDIRECT_PATH;
  }

  if (!value.startsWith("/") || value.startsWith("//")) {
    return DEFAULT_REDIRECT_PATH;
  }

  if (value.startsWith("/auth/callback")) {
    return DEFAULT_REDIRECT_PATH;
  }

  return value;
}

export default function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const provider = searchParams.get("provider") ?? "oauth";
  const incomingError = searchParams.get("error");
  const returnTo = searchParams.get("return_to");

  const [errorMessage, setErrorMessage] = useState<string | null>(
    incomingError ?? null,
  );
  const [isDone, setIsDone] = useState(false);

  const targetPath = useMemo(() => sanitizeReturnTo(returnTo), [returnTo]);

  useEffect(() => {
    const run = async () => {
      if (incomingError) {
        setErrorMessage(incomingError);
        return;
      }

      const result = await dispatch(fetchCurrentUser());

      if (fetchCurrentUser.fulfilled.match(result)) {
        setIsDone(true);
        navigate(targetPath, { replace: true });
        return;
      }

      const fallback = `Không thể hoàn tất đăng nhập với ${provider}. Vui lòng thử lại.`;
      const payloadError =
        typeof result.payload === "string" ? result.payload : fallback;
      setErrorMessage(payloadError);
    };

    run();
  }, [dispatch, incomingError, navigate, provider, targetPath]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 text-center shadow-sm">
        {!errorMessage ? (
          <>
            <div className="mb-4 flex items-center justify-center">
              {isDone ? (
                <CheckCircle2 className="h-10 w-10 text-success" />
              ) : (
                <Loader2 className="h-10 w-10 animate-spin text-primary" />
              )}
            </div>
            <h1 className="text-xl font-semibold text-foreground">
              Đang hoàn tất đăng nhập {provider}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Hệ thống đang xác thực phiên đăng nhập và đồng bộ tài khoản.
            </p>
          </>
        ) : (
          <>
            <div className="mb-4 flex items-center justify-center">
              <AlertCircle className="h-10 w-10 text-destructive" />
            </div>
            <h1 className="text-xl font-semibold text-foreground">
              Đăng nhập {provider} thất bại
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">{errorMessage}</p>
            <div className="mt-5 flex justify-center gap-2">
              <Button
                variant="outline"
                onClick={() => navigate("/login", { replace: true })}
              >
                Về trang đăng nhập
              </Button>
              <Button
                onClick={() =>
                  navigate(DEFAULT_REDIRECT_PATH, { replace: true })
                }
              >
                Về trang chủ
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
