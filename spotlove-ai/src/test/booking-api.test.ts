import { beforeEach, describe, expect, it, vi } from "vitest";

const mockBuildPaginationParams = vi.fn();

vi.mock("@/services/api/axios.client", () => {
  const mockClient = {
    get: vi.fn(),
    post: vi.fn(),
  };

  return {
    default: mockClient,
    buildPaginationParams: mockBuildPaginationParams,
  };
});

describe("bookingApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBuildPaginationParams.mockReturnValue({ page: "2", page_size: "20" });
  });

  it("should compose booking filters and call /bookings/", async () => {
    const { bookingApi } = await import("@/services/api/booking.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      get: ReturnType<typeof vi.fn>;
    };

    apiClient.get.mockResolvedValue({ data: { count: 0, results: [] } });

    await bookingApi.getBookings({
      page: 2,
      pageSize: 20,
      status: "confirmed",
      payment_status: "pending",
      vehicle_type: "Car",
      start_date: "2026-03-01",
      end_date: "2026-03-31",
    });

    expect(mockBuildPaginationParams).toHaveBeenCalled();
    expect(apiClient.get).toHaveBeenCalledWith("/bookings/", {
      params: {
        page: "2",
        page_size: "20",
        status: "confirmed",
        payment_status: "pending",
        vehicle_type: "Car",
        start_date: "2026-03-01",
        end_date: "2026-03-31",
      },
    });
  });

  it("should map upcoming bookings query and return results", async () => {
    const { bookingApi } = await import("@/services/api/booking.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      get: ReturnType<typeof vi.fn>;
    };

    apiClient.get.mockResolvedValue({
      data: {
        results: [{ id: "b1" }, { id: "b2" }],
      },
    });

    const result = await bookingApi.getUpcomingBookings();

    expect(apiClient.get).toHaveBeenCalledWith("/bookings/", {
      params: {
        booking_status: "confirmed",
        check_in_status: "not_checked_in",
        ordering: "start_time",
        page_size: 5,
      },
    });
    expect(result).toEqual([{ id: "b1" }, { id: "b2" }]);
  });

  it("should return null when booking by slot does not exist", async () => {
    const { bookingApi } = await import("@/services/api/booking.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      get: ReturnType<typeof vi.fn>;
    };

    apiClient.get.mockResolvedValue({ data: { results: [] } });

    const result = await bookingApi.getBookingBySlot("slot-a1");

    expect(result).toBeNull();
    expect(apiClient.get).toHaveBeenCalledWith("/bookings/", {
      params: {
        slot_id: "slot-a1",
        check_in_status: "checked_in",
        page_size: 1,
      },
    });
  });

  it("should normalize payment status from camelCase, snake_case and fallback", async () => {
    const { bookingApi } = await import("@/services/api/booking.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      get: ReturnType<typeof vi.fn>;
    };

    apiClient.get.mockResolvedValueOnce({
      data: { id: "b1", paymentStatus: "paid" },
    });
    apiClient.get.mockResolvedValueOnce({
      data: { id: "b2", payment_status: "completed" },
    });
    apiClient.get.mockResolvedValueOnce({ data: { id: "b3" } });

    await expect(bookingApi.pollPaymentStatus("b1")).resolves.toMatchObject({
      paymentStatus: "paid",
    });
    await expect(bookingApi.pollPaymentStatus("b2")).resolves.toMatchObject({
      paymentStatus: "completed",
    });
    await expect(bookingApi.pollPaymentStatus("b3")).resolves.toMatchObject({
      paymentStatus: "pending",
    });
  });

  it("should pass optional params for revenue endpoints", async () => {
    const { bookingApi } = await import("@/services/api/booking.api");
    const mod = await import("@/services/api/axios.client");
    const apiClient = mod.default as unknown as {
      get: ReturnType<typeof vi.fn>;
    };

    apiClient.get.mockResolvedValue({ data: { data: [{ revenue: 10 }] } });

    await bookingApi.getDailyRevenue();
    await bookingApi.getDailyRevenue(7);
    await bookingApi.getHourlyRevenue();
    await bookingApi.getHourlyRevenue("2026-03-14");

    expect(apiClient.get).toHaveBeenNthCalledWith(
      1,
      "/bookings/admin/revenue/daily/",
      { params: undefined },
    );
    expect(apiClient.get).toHaveBeenNthCalledWith(
      2,
      "/bookings/admin/revenue/daily/",
      { params: { days: 7 } },
    );
    expect(apiClient.get).toHaveBeenNthCalledWith(
      3,
      "/bookings/admin/revenue/hourly/",
      { params: undefined },
    );
    expect(apiClient.get).toHaveBeenNthCalledWith(
      4,
      "/bookings/admin/revenue/hourly/",
      { params: { date: "2026-03-14" } },
    );
  });
});
