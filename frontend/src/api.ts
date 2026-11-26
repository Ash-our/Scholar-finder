import { useEffect, useState } from "react";
import type { CatalogueResponse, Filters, Profile, MapData } from "./types";

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch("/api" + path, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new Error("تعذر الاتصال بالخدمة. تحقق من الاتصال وحاول مرة أخرى.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : "تعذر إكمال الطلب. راجع المعلومات وحاول مجددًا.",
    );
  }
  return response.json() as Promise<T>;
}

export function useCatalogue(
  filters: Filters,
  profile: Profile | null,
  page: number,
  refresh: number,
) {
  const [data, setData] = useState<CatalogueResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const key = JSON.stringify({ filters, profile, page });
  useEffect(() => {
    const controller = new AbortController();
    const snapshot = JSON.parse(key) as {
      filters: Filters;
      profile: Profile | null;
      page: number;
    };
    const query = new URLSearchParams({
      ...snapshot.filters,
      offset: String(snapshot.page * 30),
      limit: "30",
    });
    async function load() {
      setLoading(true);
      try {
        const next = await request<CatalogueResponse>(
          (snapshot.profile ? "/recommendations?" : "/scholarships?") + query,
          {
            signal: controller.signal,
            ...(snapshot.profile
              ? {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(snapshot.profile),
                }
              : {}),
          },
        );
        if (!controller.signal.aborted) {
          setData(next);
          setError("");
        }
      } catch (reason) {
        if (!controller.signal.aborted)
          setError(
            reason instanceof Error ? reason.message : "تعذر تحميل المنح",
          );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    const timer = window.setTimeout(load, 200);
    const interval = window.setInterval(load, 10_000);
    return () => {
      controller.abort();
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [key, refresh]);
  return { data, error, loading };
}

export function readProfile(): Profile | null {
  try {
    const saved = JSON.parse(
      sessionStorage.getItem("scholarship-map-profile") || "null",
    );
    return saved?.version === 1 &&
      typeof saved.profile?.nationality === "string"
      ? saved.profile
      : null;
  } catch {
    return null;
  }
}

export function useCountryOverview(filters: Filters, profile: Profile | null) {
  const [data, setData] = useState<MapData>();
  const key = JSON.stringify({
    filters: { ...filters, country: "", placement: "", bbox: "" },
    profile,
  });
  useEffect(() => {
    const controller = new AbortController();
    const snapshot = JSON.parse(key) as {
      filters: Filters;
      profile: Profile | null;
    };
    const query = new URLSearchParams({ ...snapshot.filters });
    const load = () =>
      request<MapData>("/map?" + query, {
        signal: controller.signal,
        ...(snapshot.profile
          ? {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(snapshot.profile),
            }
          : {}),
      })
        .then((value) => {
          if (!controller.signal.aborted) setData(value);
        })
        .catch(() => {});
    void load();
    const timer = setInterval(load, 10000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [key]);
  return data;
}
export function storeProfile(profile: Profile | null) {
  try {
    if (profile)
      sessionStorage.setItem(
        "scholarship-map-profile",
        JSON.stringify({ version: 1, profile }),
      );
    else sessionStorage.removeItem("scholarship-map-profile");
  } catch {
    /* Session personalization still works if browser storage is disabled. */
  }
}
