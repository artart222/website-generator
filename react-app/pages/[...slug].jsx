import fs from "fs";
import path from "path";

const COLLECTION = process.env.NEXT_PUBLIC_COLLECTION || "";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

function normalizeBasePath(basePath) {
  if (!basePath) return "";
  const withSlash = basePath.startsWith("/") ? basePath : `/${basePath}`;
  return withSlash.endsWith("/") ? withSlash.slice(0, -1) : withSlash;
}

function toSlugParts(rootRelUrl, basePath) {
  if (!rootRelUrl) return [];
  let cleaned = rootRelUrl.replace(/\/+$/, "");
  const normalizedBase = normalizeBasePath(basePath);
  if (normalizedBase && cleaned.startsWith(normalizedBase)) {
    cleaned = cleaned.slice(normalizedBase.length);
  }
  cleaned = cleaned.replace(/^\/+/, "");
  if (!cleaned) return [];
  return cleaned.split("/");
}

function buildRootRelUrl(slugParts, basePath) {
  const normalizedBase = normalizeBasePath(basePath);
  const slugPath = slugParts.length ? `/${slugParts.join("/")}` : "";
  return `${normalizedBase}${slugPath}/` || "/";
}

export async function getStaticPaths() {
  const sitePath = path.join(process.cwd(), "public", "data", "site.json");
  if (!fs.existsSync(sitePath)) {
    return { paths: [], fallback: false };
  }

  const siteData = JSON.parse(fs.readFileSync(sitePath, "utf-8"));
  const pages = Array.isArray(siteData.pages) ? siteData.pages : [];
  const filtered = COLLECTION
    ? pages.filter((page) => page.collection === COLLECTION)
    : pages;

  const paths = filtered
    .map((page) => ({
      params: { slug: toSlugParts(page.root_rel_url, BASE_PATH) },
    }))
    .filter((entry) => entry.params.slug.length > 0);

  return { paths, fallback: false };
}

export async function getStaticProps({ params }) {
  const sitePath = path.join(process.cwd(), "public", "data", "site.json");
  if (!fs.existsSync(sitePath)) {
    return { notFound: true };
  }

  const siteData = JSON.parse(fs.readFileSync(sitePath, "utf-8"));
  const pages = Array.isArray(siteData.pages) ? siteData.pages : [];
  const slugParts = params?.slug || [];
  const rootRelUrl = buildRootRelUrl(slugParts, BASE_PATH);
  const pageEntry = pages.find((page) => page.root_rel_url === rootRelUrl);

  if (!pageEntry) {
    return { notFound: true };
  }

  const pageJsonPath = path.join(process.cwd(), "public", pageEntry.json_path);
  if (!fs.existsSync(pageJsonPath)) {
    return { notFound: true };
  }

  const pageData = JSON.parse(fs.readFileSync(pageJsonPath, "utf-8"));
  return {
    props: {
      page: pageData,
    },
  };
}

export default function CollectionPage({ page }) {
  if (!page) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-16">
        <p className="text-slate-500">Page not found.</p>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-6">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
              {page.collection || "Collection"}
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">
              {page.title}
            </h1>
          </div>
          <a
            href={BASE_PATH || "/"}
            className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
          >
            Back
          </a>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl px-6 py-12">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <div
            className="space-y-4 text-slate-700 leading-7"
            dangerouslySetInnerHTML={{ __html: page.content_html }}
          />
        </div>
      </main>
    </div>
  );
}
