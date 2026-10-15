import { afterEach, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("keeps read-only inspection a GET with no request payload", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('{"status":"ok"}'));
  vi.stubGlobal("fetch", fetch);
  expect(await api("/health")).toEqual({ status: "ok" });
  expect(fetch).toHaveBeenCalledWith("/api/v1/health", {});
});

it("sends campaign intent only to the local application API", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('{"id":"draft"}'));
  vi.stubGlobal("fetch", fetch);
  await api("/campaigns", { mode: "mock" });
  expect(fetch).toHaveBeenCalledWith("/api/v1/campaigns", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: '{"mode":"mock"}',
  });
});

it("surfaces validation failures rather than treating them as success", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response('{"detail":"Confirmation budget exhausted"}', {
          status: 422,
        }),
      ),
  );
  await expect(api("/preflight", {})).rejects.toThrow(
    "Confirmation budget exhausted",
  );
});

it("turns a non-JSON gateway failure into an actionable service error", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response("<html>bad gateway</html>", { status: 502 }),
      ),
  );
  await expect(api("/health")).rejects.toThrow("HTTP 502: Service unavailable");
});
