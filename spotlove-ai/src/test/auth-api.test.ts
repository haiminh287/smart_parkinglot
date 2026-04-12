import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/services/api/axios.client", () => {
  const mockClient = {
    post: vi.fn(),
    get: vi.fn(),
  };

  return {
    default: mockClient,
    extractErrorMessage: vi.fn(() => "friendly-error"),
  };
});

describe("authApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should call login endpoint and return response data", async () => {
    const { authApi } = await import("@/services/api/auth.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      post: ReturnType<typeof vi.fn>;
    };

    apiClient.post.mockResolvedValue({
      data: { user: { id: "u1", role: "user" }, message: "ok" },
    });

    const result = await authApi.login({
      email: "user@example.com",
      password: "P@ssw0rd",
    });

    expect(apiClient.post).toHaveBeenCalledWith("/auth/login/", {
      email: "user@example.com",
      password: "P@ssw0rd",
    });
    expect(result.message).toBe("ok");
  });

  it("should wrap /auth/me response into LoginResponse shape", async () => {
    const { authApi } = await import("@/services/api/auth.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      get: ReturnType<typeof vi.fn>;
    };

      apiClient.get.mockResolvedValue({
        data: {
          id: "u2",
          email: "admin@example.com",
          username: "admin",
          role: "admin",
        },
        headers: { "content-type": "application/json" },
      });

    const result = await authApi.getCurrentUser();

    expect(apiClient.get).toHaveBeenCalledWith("/auth/me/");
    expect(result).toEqual({
      user: {
        id: "u2",
        email: "admin@example.com",
        username: "admin",
        role: "admin",
      },
      message: "Current user fetched",
    });
  });

  it("should call OAuth URL endpoints", async () => {
    const { authApi } = await import("@/services/api/auth.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      get: ReturnType<typeof vi.fn>;
    };

    apiClient.get.mockResolvedValueOnce({
      data: { authorization_url: "https://google.example/oauth" },
    });
    apiClient.get.mockResolvedValueOnce({
      data: { authorization_url: "https://facebook.example/oauth" },
    });

    await expect(authApi.getGoogleAuthUrl()).resolves.toBe(
      "https://google.example/oauth",
    );
    await expect(authApi.getFacebookAuthUrl()).resolves.toBe(
      "https://facebook.example/oauth",
    );

    expect(apiClient.get).toHaveBeenNthCalledWith(1, "/auth/google/");
    expect(apiClient.get).toHaveBeenNthCalledWith(2, "/auth/facebook/");
  });
});

describe("handleAuthError", () => {
  it("should delegate to extractErrorMessage", async () => {
    const { handleAuthError } = await import("@/services/api/auth.api");

    const message = handleAuthError({} as never);
    expect(message).toBe("friendly-error");
  });
});
