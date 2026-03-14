import { beforeEach, describe, expect, it, vi } from "vitest";

const mockBuildPaginationParams = vi.fn();

vi.mock("@/services/api/axios.client", () => {
  const mockClient = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  };

  return {
    default: mockClient,
    buildPaginationParams: mockBuildPaginationParams,
  };
});

describe("notificationApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBuildPaginationParams.mockReturnValue({ page: "1", page_size: "10" });
  });

  it("should map legacy notificationType to type and preserve existing type", async () => {
    const { notificationApi } = await import("@/services/api/notification.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      get: ReturnType<typeof vi.fn>;
    };

    apiClient.get.mockResolvedValue({
      data: {
        count: 3,
        results: [
          { id: "n1", notificationType: "payment" },
          { id: "n2", type: "booking", notificationType: "system" },
          { id: "n3" },
        ],
      },
    });

    const data = await notificationApi.getNotifications({
      page: 1,
      pageSize: 10,
      type: "system",
      isRead: false,
    });

    expect(apiClient.get).toHaveBeenCalledWith("/notifications/", {
      params: {
        page: "1",
        page_size: "10",
        type: "system",
        is_read: "false",
      },
    });

    expect(data.results[0].type).toBe("payment");
    expect(data.results[1].type).toBe("booking");
    expect(data.results[2].type).toBe("system");
  });

  it("should normalize unread count from multiple backend formats", async () => {
    const { notificationApi } = await import("@/services/api/notification.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      get: ReturnType<typeof vi.fn>;
    };

    apiClient.get.mockResolvedValueOnce({ data: { count: 5 } });
    apiClient.get.mockResolvedValueOnce({ data: { unread_count: 4 } });
    apiClient.get.mockResolvedValueOnce({ data: { unreadCount: 3 } });
    apiClient.get.mockResolvedValueOnce({ data: {} });

    await expect(notificationApi.getUnreadCount()).resolves.toEqual({
      count: 5,
    });
    await expect(notificationApi.getUnreadCount()).resolves.toEqual({
      count: 4,
    });
    await expect(notificationApi.getUnreadCount()).resolves.toEqual({
      count: 3,
    });
    await expect(notificationApi.getUnreadCount()).resolves.toEqual({
      count: 0,
    });
  });

  it("should call mark-as-read and mark-all-read endpoints", async () => {
    const { notificationApi } = await import("@/services/api/notification.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      post: ReturnType<typeof vi.fn>;
    };

    apiClient.post.mockResolvedValue({ data: {} });

    await notificationApi.markAsRead("n42");
    await notificationApi.markAllAsRead();

    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      "/notifications/mark-read/",
      {
        notification_ids: ["n42"],
      },
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      "/notifications/mark-all-read/",
    );
  });

  it("should keep delete/clear methods as silent no-op", async () => {
    const { notificationApi } = await import("@/services/api/notification.api");
    const warnSpy = vi
      .spyOn(console, "warn")
      .mockImplementation(() => undefined);

    await notificationApi.deleteNotification("n1");
    await notificationApi.clearAll();

    expect(warnSpy).toHaveBeenCalledTimes(2);
    warnSpy.mockRestore();
  });
});
