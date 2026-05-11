/**
 * WebLogger — captures ALL web activity (API calls, responses, errors, user actions)
 * to sessionStorage and lets you download as a .log file for debugging.
 *
 * SECURITY: Disabled in production. PII redacted in dev.
 */

const IS_DEV = import.meta.env.DEV;
const STORAGE_KEY = "parksmart_dev_log";
const MAX_ENTRIES = 2000;

export type LogLevel = "INFO" | "WARN" | "ERROR" | "API" | "ACTION";

export interface LogEntry {
  ts: string;
  level: LogLevel;
  tag: string;
  message: string;
  data?: unknown;
}

const REDACT_KEYS = new Set([
  "password",
  "password_confirm",
  "currentPassword",
  "newPassword",
  "token",
  "refreshToken",
  "refresh_token",
  "access_token",
  "authorization",
  "cookie",
  "session_id",
  "sessionId",
  "csrfToken",
  "X-Gateway-Secret",
  "qr_data",
  "qr_code_data",
]);

function redact(obj: unknown): unknown {
  if (obj == null || typeof obj !== "object") return obj;
  if (Array.isArray(obj)) return obj.map(redact);
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    out[k] = REDACT_KEYS.has(k) ? "[REDACTED]" : redact(v);
  }
  return out;
}

function now(): string {
  return new Date().toISOString().slice(11, 23);
}

function load(): LogEntry[] {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function save(entries: LogEntry[]): void {
  try {
    const trimmed = entries.slice(-MAX_ENTRIES);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    /* storage full — ignore */
  }
}

function append(entry: LogEntry): void {
  if (!IS_DEV) return;
  const entries = load();
  entries.push(entry);
  save(entries);
}

function formatEntry(e: LogEntry): string {
  const dataStr =
    e.data != null
      ? "\n  " + JSON.stringify(e.data, null, 2).replace(/\n/g, "\n  ")
      : "";
  return `[${e.ts}] [${e.level.padEnd(6)}] [${e.tag}] ${e.message}${dataStr}`;
}

function isAuthUrl(url: string): boolean {
  return /\/auth\/(login|register|forgot-password|reset-password)/.test(url);
}

const webLogger = {
  info(tag: string, message: string, data?: unknown) {
    if (!IS_DEV) return;
    append({ ts: now(), level: "INFO", tag, message, data: redact(data) });
    console.log(`[${tag}]`, message, data != null ? redact(data) : "");
  },

  warn(tag: string, message: string, data?: unknown) {
    if (!IS_DEV) return;
    append({ ts: now(), level: "WARN", tag, message, data: redact(data) });
    console.warn(`[${tag}]`, message, data != null ? redact(data) : "");
  },

  error(tag: string, message: string, data?: unknown) {
    if (!IS_DEV) return;
    append({ ts: now(), level: "ERROR", tag, message, data: redact(data) });
    console.error(`[${tag}]`, message, data != null ? redact(data) : "");
  },

  apiReq(method: string, url: string, body?: unknown) {
    if (!IS_DEV) return;
    const safeData = isAuthUrl(url) ? "[AUTH-REDACTED]" : redact(body);
    append({
      ts: now(),
      level: "API",
      tag: "REQ",
      message: `→ ${method.toUpperCase()} ${url}`,
      data: safeData,
    });
    console.log(`[API REQ] ${method.toUpperCase()} ${url}`, safeData ?? "");
  },

  apiRes(
    method: string,
    url: string,
    status: number,
    duration: number,
    data?: unknown,
  ) {
    if (!IS_DEV) return;
    const safeData = isAuthUrl(url) ? "[AUTH-REDACTED]" : redact(data);
    append({
      ts: now(),
      level: "API",
      tag: "RSP",
      message: `← ${method.toUpperCase()} ${url} ${status} (${duration}ms)`,
      data: safeData,
    });
    console.log(
      `[API RSP] ${method.toUpperCase()} ${url} ${status} (${duration}ms)`,
      safeData ?? "",
    );
  },

  apiErr(
    method: string,
    url: string,
    status: number,
    duration: number,
    data?: unknown,
  ) {
    if (!IS_DEV) return;
    const safeData = redact(data);
    append({
      ts: now(),
      level: "ERROR",
      tag: "RSP",
      message: `✗ ${method.toUpperCase()} ${url} ${status} (${duration}ms)`,
      data: safeData,
    });
    console.error(
      `[API ERR] ${method.toUpperCase()} ${url} ${status} (${duration}ms)`,
      safeData ?? "",
    );
  },

  action(action: string, detail?: unknown) {
    if (!IS_DEV) return;
    append({
      ts: now(),
      level: "ACTION",
      tag: "UI",
      message: action,
      data: redact(detail),
    });
    console.log(`[ACTION]`, action, detail != null ? redact(detail) : "");
  },

  dump(): string {
    const entries = load();
    const header = [
      "=".repeat(60),
      `ParkSmart Dev Log  —  ${new Date().toLocaleString()}`,
      `Entries: ${entries.length}`,
      "=".repeat(60),
      "",
    ].join("\n");
    return header + entries.map(formatEntry).join("\n");
  },

  download() {
    if (!IS_DEV) {
      console.warn("[webLogger] download disabled in production");
      return;
    }
    const text = this.dump();
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `parksmart_${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}.log`;
    a.click();
    URL.revokeObjectURL(url);
  },

  clear() {
    sessionStorage.removeItem(STORAGE_KEY);
  },

  count(): number {
    return load().length;
  },
};

export default webLogger;
