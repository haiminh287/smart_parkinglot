/**
 * Smoke test — verifies the App component renders without crashing.
 * This is the most basic test to ensure the application bootstraps correctly.
 */

import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import App from "@/App";

// Mock react-router-dom to avoid route issues in test
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    BrowserRouter: ({ children }: { children: React.ReactNode }) => (
      <>{children}</>
    ),
    Routes: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Route: () => null,
  };
});

// Mock heavy context providers
vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

vi.mock("@/components/layout/ProtectedRoute", () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

vi.mock("@/components/support/ContactWidget", () => ({
  ContactWidget: () => null,
}));

vi.mock("@/components/effects/SnowfallEffect", () => ({
  SnowfallEffect: () => null,
}));

describe("App Smoke Test", () => {
  it("renders without crashing", () => {
    const { container } = render(<App />);
    expect(container).toBeTruthy();
  });
});
