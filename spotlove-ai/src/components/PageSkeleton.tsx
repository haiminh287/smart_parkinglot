export function PageSkeleton() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="animate-pulse text-muted-foreground">Đang tải...</div>
    </div>
  );
}
