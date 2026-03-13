import { useState, useEffect } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Users,
  Search,
  Plus,
  MoreVertical,
  Edit2,
  Trash2,
  Shield,
  Mail,
  Phone,
  Calendar,
  Car,
  Ban,
  CheckCircle,
  Grid3X3,
  List,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  adminApi,
  type User,
  type CreateUserData,
} from "@/services/api/admin.api";
import { useToast } from "@/hooks/use-toast";

type ViewMode = "grid" | "list";

interface UserDisplay extends Omit<User, "createdAt" | "lastLogin"> {
  status: "active" | "banned";
  totalSpent: number;
  createdAt: Date;
}

interface EditFormData {
  username: string;
  email: string;
  phone: string;
  role: "user" | "admin";
  isActive: boolean;
}

interface AddFormData {
  email: string;
  username: string;
  password: string;
  role: "user" | "admin";
  phone: string;
}

const INITIAL_ADD_FORM: AddFormData = {
  email: "",
  username: "",
  password: "",
  role: "user",
  phone: "",
};

export default function AdminUsersPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<UserDisplay[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterRole, setFilterRole] = useState<"all" | "user" | "admin">("all");
  const [filterStatus, setFilterStatus] = useState<"all" | "active" | "banned">(
    "all",
  );
  const [selectedUser, setSelectedUser] = useState<UserDisplay | null>(null);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [editForm, setEditForm] = useState<EditFormData>({
    username: "",
    email: "",
    phone: "",
    role: "user",
    isActive: true,
  });
  const [addForm, setAddForm] = useState<AddFormData>(INITIAL_ADD_FORM);
  const [isSaving, setIsSaving] = useState(false);

  // Fetch users from API
  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await adminApi.getUsers({
        page: 1,
        pageSize: 100,
      });

      // Map API response to UserDisplay format
      const mappedUsers: UserDisplay[] = response.results.map((user) => {
        // Backend sends dateJoined (from Django AbstractUser), not createdAt
        const rawDate = user.dateJoined || user.createdAt;
        return {
          ...user,
          role: (user.role === "staff" ? "admin" : user.role) as
            | "user"
            | "admin",
          status: user.isActive ? "active" : "banned",
          totalBookings: user.totalBookings || 0,
          totalSpent: user.totalSpent || 0,
          createdAt: rawDate ? new Date(rawDate) : new Date(),
          noShowCount: user.noShowCount || 0,
        };
      });

      setUsers(mappedUsers);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      console.error("Failed to fetch users:", error);
      setError(
        error.response?.data?.message || "Không thể tải danh sách người dùng",
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle ban/unban user
  const handleToggleBan = async (userId: string, currentStatus: string) => {
    try {
      if (currentStatus === "banned") {
        await adminApi.activateUser(userId);
        toast({
          title: "Thành công",
          description: "Đã bỏ cấm người dùng",
        });
      } else {
        await adminApi.deactivateUser(userId);
        toast({
          title: "Thành công",
          description: "Đã cấm người dùng",
        });
      }
      await fetchUsers();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      toast({
        variant: "destructive",
        title: "Lỗi",
        description:
          error.response?.data?.message || "Không thể thực hiện thao tác",
      });
    }
  };

  // Reset no-show count
  const handleResetNoShow = async (userId: string) => {
    try {
      await adminApi.resetNoShowCount(userId);
      toast({
        title: "Thành công",
        description: "Đã reset vi phạm",
      });
      await fetchUsers();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: error.response?.data?.message || "Không thể reset vi phạm",
      });
    }
  };

  // Update user
  const handleUpdateUser = async () => {
    if (!selectedUser) return;
    try {
      setIsSaving(true);
      const updateData: Partial<User> = {};
      // Only send changed fields
      if (editForm.username !== selectedUser.username)
        updateData.username = editForm.username;
      if (editForm.email !== selectedUser.email)
        updateData.email = editForm.email;
      if (editForm.phone !== (selectedUser.phone ?? ""))
        updateData.phone = editForm.phone;
      if (editForm.role !== selectedUser.role) updateData.role = editForm.role;
      if (editForm.isActive !== selectedUser.isActive)
        updateData.isActive = editForm.isActive;

      if (Object.keys(updateData).length === 0) {
        toast({
          title: "Thông báo",
          description: "Không có thay đổi nào",
        });
        setShowEditDialog(false);
        return;
      }

      await adminApi.updateUser(selectedUser.id, updateData);
      toast({
        title: "Thành công",
        description: "Đã cập nhật thông tin người dùng",
      });
      setShowEditDialog(false);
      await fetchUsers();
    } catch (err: unknown) {
      const error = err as {
        response?: { data?: Record<string, string[]> | { detail?: string } };
      };
      const errData = error.response?.data;
      let msg = "Không thể cập nhật người dùng";
      if (errData) {
        if ("detail" in errData && errData.detail) {
          msg = errData.detail;
        } else {
          const firstKey = Object.keys(errData)[0];
          if (
            firstKey &&
            Array.isArray((errData as Record<string, string[]>)[firstKey])
          ) {
            msg = `${firstKey}: ${(errData as Record<string, string[]>)[firstKey][0]}`;
          }
        }
      }
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: msg,
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Create user
  const handleCreateUser = async () => {
    // Validate required fields
    if (!addForm.email || !addForm.username || !addForm.password) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Vui lòng điền đầy đủ email, tên người dùng và mật khẩu",
      });
      return;
    }
    try {
      setIsSaving(true);
      const createData: CreateUserData = {
        email: addForm.email,
        username: addForm.username,
        password: addForm.password,
        role: addForm.role,
      };
      if (addForm.phone) createData.phone = addForm.phone;

      await adminApi.createUser(createData);
      toast({
        title: "Thành công",
        description: "Đã tạo người dùng mới",
      });
      setShowAddDialog(false);
      setAddForm(INITIAL_ADD_FORM);
      await fetchUsers();
    } catch (err: unknown) {
      const error = err as {
        response?: { data?: Record<string, string[]> | { detail?: string } };
      };
      const errData = error.response?.data;
      let msg = "Không thể tạo người dùng";
      if (errData) {
        if ("detail" in errData && errData.detail) {
          msg = errData.detail;
        } else {
          const firstKey = Object.keys(errData)[0];
          if (
            firstKey &&
            Array.isArray((errData as Record<string, string[]>)[firstKey])
          ) {
            msg = `${firstKey}: ${(errData as Record<string, string[]>)[firstKey][0]}`;
          }
        }
      }
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: msg,
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Load users on mount
  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = users.filter((user) => {
    const matchesSearch =
      user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (user.phone ?? "").includes(searchQuery);
    const matchesRole = filterRole === "all" || user.role === filterRole;
    const matchesStatus =
      filterStatus === "all" || user.status === filterStatus;
    return matchesSearch && matchesRole && matchesStatus;
  });

  const getStatusBadge = (status: UserDisplay["status"]) => {
    switch (status) {
      case "active":
        return (
          <Badge className="bg-success/10 text-success border-success/20">
            Hoạt động
          </Badge>
        );
      case "banned":
        return <Badge variant="destructive">Đã cấm</Badge>;
    }
  };

  const UserCard = ({ user }: { user: UserDisplay }) => (
    <div className="rounded-2xl border border-border bg-card p-4 hover:border-primary/30 transition-all hover:shadow-md">
      {/* Header with Avatar and Menu */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <Avatar className="h-12 w-12">
            <AvatarImage src={user.avatar} alt={user.username} />
            <AvatarFallback className="bg-primary text-primary-foreground text-lg">
              {user.username.charAt(0)}
            </AvatarFallback>
          </Avatar>
          <div>
            <p className="font-semibold text-foreground">{user.username}</p>
            <Badge
              variant="outline"
              className={cn(
                "text-xs mt-1",
                user.role === "admin"
                  ? "bg-destructive/10 text-destructive border-destructive/20"
                  : "bg-primary/10 text-primary border-primary/20",
              )}
            >
              <Shield className="h-3 w-3 mr-1" />
              {user.role === "admin" ? "Admin" : "User"}
            </Badge>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() => {
                setSelectedUser(user);
                setEditForm({
                  username: user.username,
                  email: user.email,
                  phone: user.phone ?? "",
                  role: user.role,
                  isActive: user.isActive,
                });
                setShowEditDialog(true);
              }}
            >
              <Edit2 className="h-4 w-4 mr-2" />
              Chỉnh sửa
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleResetNoShow(user.id)}>
              <Calendar className="h-4 w-4 mr-2" />
              Reset vi phạm ({user.noShowCount})
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {user.status === "banned" ? (
              <DropdownMenuItem
                className="text-success"
                onClick={() => handleToggleBan(user.id, user.status)}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Bỏ cấm
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem
                className="text-warning"
                onClick={() => handleToggleBan(user.id, user.status)}
              >
                <Ban className="h-4 w-4 mr-2" />
                Cấm người dùng
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Contact Info */}
      <div className="space-y-2 mb-3">
        <div className="flex items-center gap-2 text-sm">
          <Mail className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground truncate">{user.email}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Phone className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">{user.phone}</span>
        </div>
      </div>

      {/* Status and Stats */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        {getStatusBadge(user.status)}
        <div className="text-right">
          <div className="flex items-center gap-1 text-sm">
            <Car className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="font-medium text-foreground">
              {user.totalBookings}
            </span>
            <span className="text-muted-foreground">booking</span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Chi tiêu:{" "}
            {new Intl.NumberFormat("vi-VN").format(user.totalSpent || 0)}đ
          </p>
        </div>
      </div>

      {/* Join Date */}
      <p className="text-xs text-muted-foreground mt-2">
        Tham gia: {user.createdAt.toLocaleDateString("vi-VN")}
      </p>
    </div>
  );

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Quản lý người dùng
            </h1>
            <p className="mt-1 text-muted-foreground">
              {users.length} người dùng trong hệ thống
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="hidden sm:flex items-center gap-1 rounded-lg border border-border p-1">
              <Button
                variant={viewMode === "grid" ? "secondary" : "ghost"}
                size="icon"
                className="h-8 w-8"
                onClick={() => setViewMode("grid")}
              >
                <Grid3X3 className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === "list" ? "secondary" : "ghost"}
                size="icon"
                className="h-8 w-8"
                onClick={() => setViewMode("list")}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
            <Button
              className="gradient-primary gap-2"
              onClick={() => {
                setAddForm(INITIAL_ADD_FORM);
                setShowAddDialog(true);
              }}
            >
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">Thêm người dùng</span>
              <span className="sm:hidden">Thêm</span>
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Tìm theo tên, email hoặc SĐT..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-border bg-card pl-10 pr-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <select
            value={filterRole}
            onChange={(e) =>
              setFilterRole(e.target.value as "all" | "user" | "admin")
            }
            className="rounded-xl border border-border bg-card px-4 py-2.5 focus:border-primary focus:outline-none text-sm"
          >
            <option value="all">Tất cả vai trò</option>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) =>
              setFilterStatus(e.target.value as "all" | "active" | "banned")
            }
            className="rounded-xl border border-border bg-card px-4 py-2.5 focus:border-primary focus:outline-none text-sm"
          >
            <option value="all">Tất cả trạng thái</option>
            <option value="active">Hoạt động</option>
            <option value="banned">Đã cấm</option>
          </select>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="mt-4 text-muted-foreground">Đang tải...</p>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Users className="h-12 w-12 text-destructive mb-4" />
            <p className="text-lg font-semibold text-foreground">
              Có lỗi xảy ra
            </p>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={fetchUsers}>Thử lại</Button>
          </div>
        )}

        {/* Users Grid - Always use grid layout, responsive columns */}
        {!isLoading && !error && (
          <div
            className={cn(
              "grid gap-4",
              viewMode === "grid"
                ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
                : "grid-cols-1",
            )}
          >
            {filteredUsers.map((user) => (
              <UserCard key={user.id} user={user} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && filteredUsers.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Users className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold text-foreground">
              Không tìm thấy người dùng
            </p>
            <p className="text-muted-foreground">
              Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm
            </p>
          </div>
        )}
      </div>

      {/* Edit User Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chỉnh sửa người dùng</DialogTitle>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <Avatar className="h-16 w-16">
                  <AvatarImage
                    src={selectedUser.avatar}
                    alt={selectedUser.username}
                  />
                  <AvatarFallback className="bg-primary text-primary-foreground text-xl">
                    {selectedUser.username.charAt(0)}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-semibold text-lg">
                    {selectedUser.username}
                  </p>
                  <Badge
                    variant="outline"
                    className={cn(
                      selectedUser.role === "admin"
                        ? "bg-destructive/10 text-destructive border-destructive/20"
                        : "bg-primary/10 text-primary border-primary/20",
                    )}
                  >
                    {selectedUser.role === "admin" ? "Admin" : "User"}
                  </Badge>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-foreground">
                    Tên người dùng
                  </label>
                  <input
                    type="text"
                    value={editForm.username}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        username: e.target.value,
                      }))
                    }
                    className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                    data-testid="edit-username"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground">
                    Email
                  </label>
                  <input
                    type="email"
                    value={editForm.email}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        email: e.target.value,
                      }))
                    }
                    className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                    data-testid="edit-email"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground">
                    Số điện thoại
                  </label>
                  <input
                    type="tel"
                    value={editForm.phone}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        phone: e.target.value,
                      }))
                    }
                    className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                    data-testid="edit-phone"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground">
                    Vai trò
                  </label>
                  <select
                    value={editForm.role}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        role: e.target.value as "user" | "admin",
                      }))
                    }
                    className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                    data-testid="edit-role"
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground">
                    Trạng thái
                  </label>
                  <select
                    value={editForm.isActive ? "active" : "inactive"}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        isActive: e.target.value === "active",
                      }))
                    }
                    className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                    data-testid="edit-status"
                  >
                    <option value="active">Hoạt động</option>
                    <option value="inactive">Không hoạt động</option>
                  </select>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Hủy
            </Button>
            <Button
              className="gradient-primary"
              disabled={isSaving}
              onClick={handleUpdateUser}
              data-testid="edit-save-btn"
            >
              {isSaving ? "Đang lưu..." : "Lưu thay đổi"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add User Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Thêm người dùng mới</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-foreground">
                Email <span className="text-destructive">*</span>
              </label>
              <input
                type="email"
                value={addForm.email}
                onChange={(e) =>
                  setAddForm((prev) => ({ ...prev, email: e.target.value }))
                }
                placeholder="user@example.com"
                className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                data-testid="add-email"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">
                Tên người dùng <span className="text-destructive">*</span>
              </label>
              <input
                type="text"
                value={addForm.username}
                onChange={(e) =>
                  setAddForm((prev) => ({ ...prev, username: e.target.value }))
                }
                placeholder="username"
                className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                data-testid="add-username"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">
                Mật khẩu <span className="text-destructive">*</span>
              </label>
              <input
                type="password"
                value={addForm.password}
                onChange={(e) =>
                  setAddForm((prev) => ({ ...prev, password: e.target.value }))
                }
                placeholder="Nhập mật khẩu"
                className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                data-testid="add-password"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">
                Vai trò
              </label>
              <select
                value={addForm.role}
                onChange={(e) =>
                  setAddForm((prev) => ({
                    ...prev,
                    role: e.target.value as "user" | "admin",
                  }))
                }
                className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                data-testid="add-role"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">
                Số điện thoại
              </label>
              <input
                type="tel"
                value={addForm.phone}
                onChange={(e) =>
                  setAddForm((prev) => ({ ...prev, phone: e.target.value }))
                }
                placeholder="0901234567"
                className="w-full mt-1 rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                data-testid="add-phone"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowAddDialog(false);
                setAddForm(INITIAL_ADD_FORM);
              }}
            >
              Hủy
            </Button>
            <Button
              className="gradient-primary"
              disabled={isSaving}
              onClick={handleCreateUser}
              data-testid="add-save-btn"
            >
              {isSaving ? "Đang tạo..." : "Tạo người dùng"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
