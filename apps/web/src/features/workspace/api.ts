import type { Session } from "./types";
let csrf = "";
export function apiBase() {
  return (
    import.meta.env["VITE_API_URL"] ||
    (typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : "http://localhost:8000")
  );
}
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, {
    method: body === undefined ? "GET" : "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(body === undefined ? {} : { "X-CSRF-Token": csrf }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    ...(signal ? { signal } : {}),
  });
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: "Your session expired. Sign in to your workspace again.",
      403: "This action requires an authorized reviewer or project credential.",
      409: "The case or reviewed artifacts changed. Refresh and review the current result.",
      422: "The server could not accept these inputs. Check the selected agent, mode and source.",
      429: "The server is busy. Wait a moment before trying again.",
    };
    throw new ApiError(
      response.status,
      (path === "/v1/auth/session" && body !== undefined && response.status === 401
        ? "Workspace sign-in failed. Check your access key and try again."
        : messages[response.status]) ||
        `The backend request failed (${response.status}). Check the connection and try again.`,
    );
  }
  return response.json();
}
export async function restoreSession(signal?: AbortSignal) {
  const session = await api<Session>("/v1/auth/session", undefined, signal);
  csrf = session.csrf_token;
  return session;
}
export async function login(api_key: string) {
  const session = await api<Session>("/v1/auth/session", { api_key });
  csrf = session.csrf_token;
  return session;
}
export async function logout() {
  await api("/v1/auth/logout", {});
  csrf = "";
}
export function download(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([prettyJson(value)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}
