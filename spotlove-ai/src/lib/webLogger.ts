/**
 * WebLogger — captures ALL web activity (API calls, responses, errors, user actions)
 * to localStorage and lets you download as a .log file for debugging.
 *
 * Usage: webLogger.info / .warn / .error / .api / .action
 * Export: webLogger.download()  — triggers browser download of full session log
 */

const STORAGE_KEY = "parksmart_dev_log";
const MAX_ENTRIES = 2000;

export type LogLevel = "INFO" | "WARN" | "ERROR" | "API" | "ACTION";

export interface LogEntry {
  ts: string; // HH:mm:ss.SSS
  level: LogLevel;
  tag: string;
  message: string;
  data?: unknown;
}

function now(): string {
  return new Date().toISOString().slice(11, 23); // HH:mm:ss.SSS
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
    // Keep only last MAX_ENTRIES to avoid storage overflow
    const trimmed = entries.slice(-MAX_ENTRIES);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    /* storage full — ignore */
  }
}

function append(entry: LogEntry): void {
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

const webLogger = {
  info(tag: string, message: string, data?: unknown) {
    append({ ts: now(), level: "INFO", tag, message, data });
    console.log(`[${tag}]`, message, data ?? "");
  },

  warn(tag: string, message: string, data?: unknown) {
    append({ ts: now(), level: "WARN", tag, message, data });
    console.warn(`[${tag}]`, message, data ?? "");
  },

  error(tag: string, message: string, data?: unknown) {
    append({ ts: now(), level: "ERROR", tag, message, data });
    console.error(`[${tag}]`, message, data ?? "");
  },

  /** Log an API request about to be sent */
  apiReq(method: string, url: string, body?: unknown) {
    append({
      ts: now(),
      level: "API",
      tag: "REQ",
      message: `→ ${method.toUpperCase()} ${url}`,
      data: body,
    });
    console.log(`[API REQ] ${method.toUpperCase()} ${url}`, body ?? "");
  },

  /** Log a successful API response */
  apiRes(
    method: string,
    url: string,
    status: number,
    duration: number,
    data?: unknown,
  ) {
    append({
      ts: now(),
      level: "API",
      tag: "RSP",
      message: `← ${method.toUpperCase()} ${url} ${status} (${duration}ms)`,
      data,
    });
    console.log(
      `[API RSP] ${method.toUpperCase()} ${url} ${status} (${duration}ms)`,
      data ?? "",
    );
  },

  /** Log a failed API response */
  apiErr(
    method: string,
    url: string,
    status: number,
    duration: number,
    data?: unknown,
  ) {
    append({
      ts: now(),
      level: "ERROR",
      tag: "RSP",
      message: `✗ ${method.toUpperCase()} ${url} ${status} (${duration}ms)`,
      data,
    });
    console.error(
      `[API ERR] ${method.toUpperCase()} ${url} ${status} (${duration}ms)`,
      data ?? "",
    );
  },

  /** Log a user action (click, navigation, form submit) */
  action(action: string, detail?: unknown) {
    append({
      ts: now(),
      level: "ACTION",
      tag: "UI",
      message: action,
      data: detail,
    });
    console.log(`[ACTION]`, action, detail ?? "");
  },

  /** Return all entries as plain text */
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

  /** Trigger browser download of the full log */
  download() {
    const text = this.dump();
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `parksmart_${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}.log`;
    a.click();
    URL.revokeObjectURL(url);
  },

  /** Clear all stored entries */
  clear() {
    sessionStorage.removeItem(STORAGE_KEY);
  },

  /** Get count of stored entries */
  count(): number {
    return load().length;
  },
};

export default webLogger;
