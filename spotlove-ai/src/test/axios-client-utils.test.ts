import { describe, expect, it } from "vitest";
import {
  buildPaginationParams,
  extractErrorMessage,
} from "@/services/api/axios.client";

describe("buildPaginationParams", () => {
  it("should map camelCase pageSize into page_size", () => {
    const result = buildPaginationParams({
      page: 3,
      pageSize: 25,
      ordering: "-created_at",
      search: "abc",
    });

    expect(result).toEqual({
      page: "3",
      page_size: "25",
      ordering: "-created_at",
      search: "abc",
    });
  });

  it("should return empty object for empty params", () => {
    expect(buildPaginationParams({})).toEqual({});
  });
});

describe("extractErrorMessage", () => {
  it("should prioritize detail, message, non_field_errors and field errors", () => {
    expect(
      extractErrorMessage({
        response: { data: { detail: "detail-msg" } },
      } as never),
    ).toBe("detail-msg");

    expect(
      extractErrorMessage({
        response: { data: { message: "message-msg" } },
      } as never),
    ).toBe("message-msg");

    expect(
      extractErrorMessage({
        response: { data: { non_field_errors: ["non-field-msg"] } },
      } as never),
    ).toBe("non-field-msg");

    expect(
      extractErrorMessage({
        response: {
          data: {
            errors: {
              email: ["email invalid"],
            },
          },
        },
      } as never),
    ).toBe("email invalid");
  });

  it("should map status codes to localized defaults", () => {
    expect(extractErrorMessage({ response: { status: 400 } } as never)).toBe(
      "Dữ liệu không hợp lệ",
    );
    expect(extractErrorMessage({ response: { status: 401 } } as never)).toBe(
      "Vui lòng đăng nhập lại",
    );
    expect(extractErrorMessage({ response: { status: 403 } } as never)).toBe(
      "Bạn không có quyền thực hiện thao tác này",
    );
    expect(extractErrorMessage({ response: { status: 404 } } as never)).toBe(
      "Không tìm thấy dữ liệu",
    );
    expect(extractErrorMessage({ response: { status: 500 } } as never)).toBe(
      "Lỗi hệ thống, vui lòng thử lại sau",
    );
  });

  it("should return generic fallback when error shape is empty", () => {
    expect(extractErrorMessage({} as never)).toBe(
      "Có lỗi xảy ra, vui lòng thử lại",
    );
  });
});
