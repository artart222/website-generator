import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

const DATA_URL = process.env.NEXT_PUBLIC_DATA_URL || "/data";
const COLLECTION = process.env.NEXT_PUBLIC_COLLECTION || "";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

function normalizeBasePath(basePath) {
  if (!basePath) return "";
  const withSlash = basePath.startsWith("/") ? basePath : `/${basePath}`;
  return withSlash.endsWith("/") ? withSlash.slice(0, -1) : withSlash;
}

function stripBasePath(urlPath, basePath) {
  if (!urlPath) return "/";
  const normalizedBase = normalizeBasePath(basePath);
  if (normalizedBase && urlPath.startsWith(normalizedBase)) {
    const stripped = urlPath.slice(normalizedBase.length);
    return stripped.startsWith("/") ? stripped : `/${stripped}`;
  }
  return urlPath;
}

function normalizeText(value) {
  if (!value) return "";
  return String(value);
}

export default function CollectionIndex() {
  const [siteData, setSiteData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${DATA_URL}/site.json`)
      .then((res) => res.json())
      .then((data) => setSiteData(data))
      .catch((err) => setError(err.message || "Failed to load data."));
  }, []);

  const entries = useMemo(() => {
    if (!siteData || !Array.isArray(siteData.pages)) return [];
    if (!COLLECTION) return siteData.pages;
    return siteData.pages.filter((page) => page.collection === COLLECTION);
  }, [siteData]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-6">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
              {normalizeText(COLLECTION || "Collection")}
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">
              React Section
            </h1>
          </div>
          <a
            href="/"
            className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
          >
            Back to site
          </a>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-2 text-sm text-slate-500">
          <span>Data source</span>
          <code className="w-fit rounded bg-slate-100 px-3 py-1 text-xs text-slate-700">
            {DATA_URL}/site.json
          </code>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}
        {!siteData && !error && (
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
            Loading data...
          </div>
        )}

        <ul className="mt-8 grid gap-4 md:grid-cols-2">
          {entries.map((page) => {
            const href = stripBasePath(page.root_rel_url, BASE_PATH) || "/";
            return (
              <li
                key={page.json_path}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <h2 className="text-lg font-semibold text-slate-900">
                  <Link href={href} className="hover:underline">
                    {page.title}
                  </Link>
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                  Type: {page.type || "item"}
                </p>
                <Link
                  href={href}
                  className="mt-4 inline-flex items-center text-sm font-medium text-slate-900"
                >
                  View details {"->"}
                </Link>
              </li>
            );
          })}
        </ul>
      </main>
    </div>
  );
}
