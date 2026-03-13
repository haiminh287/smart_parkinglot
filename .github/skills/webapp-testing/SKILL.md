---
name: webapp-testing
description: 'Bộ công cụ kiểm thử giao diện web (End-to-End Testing). Sử dụng khi cần verify UI, tương tác form, tìm lỗi render, hoặc kiểm tra responsive trên trình duyệt.'
---

# 🎭 Kỹ năng Kiểm thử Giao diện Web (Playwright E2E Testing)

## Mục đích
Skill này cung cấp quy trình chuẩn để kiểm thử giao diện người dùng (UI) bằng **Playwright** — framework E2E testing hiện đại nhất.

## Điều kiện Kích hoạt
Sử dụng skill này khi:
- Cần verify giao diện người dùng (UI rendering)
- Cần test tương tác form (submit, validation)
- Cần kiểm tra responsive design (mobile, tablet, desktop)
- Cần test navigation và routing
- Cần chụp ảnh màn hình khi phát hiện lỗi

## Quy trình Thực hiện

### 1. Kiểm tra Môi trường
```bash
# Đảm bảo Playwright đã được cài đặt
npx playwright --version || npx playwright install

# Đảm bảo máy chủ cục bộ (dev server) đang chạy
curl -s http://localhost:3000/health || echo "Server chưa chạy!"
```

### 2. Cấu trúc Thư mục Test
```
tests/
├── e2e/
│   ├── fixtures/          # Test fixtures & setup
│   │   └── test-data.ts
│   ├── pages/             # Page Object Models
│   │   ├── login.page.ts
│   │   ├── dashboard.page.ts
│   │   └── base.page.ts
│   ├── specs/             # Test specifications
│   │   ├── auth.spec.ts
│   │   ├── dashboard.spec.ts
│   │   └── navigation.spec.ts
│   └── helpers/           # Utility helpers
│       └── test-utils.ts
└── playwright.config.ts
```

### 3. Cấu hình Playwright
```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e/specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 13'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### 4. Page Object Model Template
```typescript
// tests/e2e/pages/base.page.ts
import { Page, Locator, expect } from '@playwright/test';

export class BasePage {
  constructor(protected page: Page) {}

  async navigateTo(path: string) {
    await this.page.goto(path);
    await this.page.waitForLoadState('networkidle');
  }

  async getTitle(): Promise<string> {
    return this.page.title();
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `test-results/screenshots/${name}.png`,
      fullPage: true 
    });
  }

  async waitForElement(selector: string, timeout = 10000) {
    await this.page.waitForSelector(selector, { timeout });
  }
}
```

### 5. Viết Test Specifications
```typescript
// tests/e2e/specs/auth.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';

test.describe('Authentication Flow', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.navigateTo('/login');
  });

  test('should display login form', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /đăng nhập/i })).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Mật khẩu')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await loginPage.login('invalid@email.com', 'wrongpassword');
    await expect(page.getByText(/thông tin đăng nhập không đúng/i)).toBeVisible();
  });

  test('should redirect to dashboard on successful login', async ({ page }) => {
    await loginPage.login('admin@example.com', 'validpassword');
    await expect(page).toHaveURL('/dashboard');
  });
});
```

### 6. Chạy Tests
```bash
# Chạy tất cả E2E tests
npx playwright test

# Chạy trên browser cụ thể
npx playwright test --project=chromium

# Chạy với UI mode (debug)
npx playwright test --ui

# Xem report
npx playwright show-report
```

### 7. Quy tắc Quan trọng
- ✅ **LUÔN** sử dụng Page Object Model
- ✅ **LUÔN** chụp screenshot khi test fail
- ✅ **LUÔN** test trên multiple browsers (cross-browser)
- ✅ **LUÔN** test responsive (mobile + desktop)
- ❌ **KHÔNG** sử dụng `page.waitForTimeout()` – dùng explicit waits thay thế
- ❌ **KHÔNG** test implementation details – test user behavior
