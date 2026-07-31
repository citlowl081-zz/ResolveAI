"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Navbar from "@/lib/navbar";
import { products, type Product } from "@/lib/api";
import { CATEGORIES, catalogByName } from "@/config/catalog";
import { PlannedImage } from "@/components/image-placeholder";
import { formatCurrency, formatNumber, friendlyError } from "@/lib/labels";
export default function ProductsPage() {
  const [selected, setSelected] = useState(""),
    [query, setQuery] = useState(""),
    [items, setItems] = useState<Product[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    setSelected(p.get("category") || "");
    setQuery(p.get("q") || "");
    products
      .listAll()
      .then((all) => setItems(all.filter((x) => catalogByName(x.name))))
      .catch((e) => setError(friendlyError(e)))
      .finally(() => setLoading(false));
  }, []);
  const visible = useMemo(
    () =>
      items.filter(
        (p) =>
          (!selected || catalogByName(p.name)?.category === selected) &&
          (!query ||
            `${p.name} ${p.description || ""}`
              .toLowerCase()
              .includes(query.toLowerCase())),
      ),
    [items, query, selected],
  );
  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl p-5 md:p-8">
        <header className="border-b pb-6">
          <p className="font-semibold text-blue-600">智能数码与桌面办公</p>
          <h1 className="mt-1 text-3xl font-black">精选商品</h1>
          <div className="mt-5 flex flex-col gap-3 md:flex-row">
            <input
              aria-label="搜索商品"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索商品名称或卖点"
              className="rounded-md border px-3 py-2 text-sm md:w-80"
            />
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelected("")}
                className={`rounded-md border px-3 py-2 text-sm ${!selected ? "bg-slate-900 text-white" : "bg-white"}`}
              >
                全部
              </button>
              {CATEGORIES.map((c) => (
                <button
                  key={c.slug}
                  onClick={() => setSelected(c.slug)}
                  className={`rounded-md border px-3 py-2 text-sm ${selected === c.slug ? "bg-slate-900 text-white" : "bg-white"}`}
                >
                  {c.name}
                </button>
              ))}
            </div>
          </div>
          <p className="mt-3 text-sm text-slate-500">
            共 {formatNumber(visible.length)} 件商品
          </p>
        </header>
        {loading && (
          <p className="py-16 text-center text-slate-500">正在加载商品…</p>
        )}
        {error && <p className="py-16 text-center text-red-600">{error}</p>}
        <div className="grid grid-cols-2 gap-3 py-8 sm:gap-5 lg:grid-cols-4">
          {visible.map((p) => {
            const m = catalogByName(p.name);
            return (
              <Link
                key={p.id}
                href={`/products/${p.id}`}
                className="overflow-hidden rounded-lg border bg-white shadow-sm hover:shadow-md"
              >
                <PlannedImage
                  src={
                    m?.image ||
                    p.image_url ||
                    "/images/products/unplanned/main.webp"
                  }
                  alt={`${p.name}主图`}
                />
                <div className="p-3 sm:p-4">
                  <p className="text-xs text-blue-600">
                    {CATEGORIES.find((c) => c.slug === m?.category)?.name ||
                      "智能数码"}
                  </p>
                  <h2 className="mt-1 min-h-12 font-semibold">{p.name}</h2>
                  <p className="line-clamp-1 text-sm text-slate-500">
                    {m?.sellingPoint || p.description}
                  </p>
                  <div className="mt-3 flex flex-wrap items-end justify-between gap-1">
                    <strong className="text-lg text-blue-600 sm:text-xl">
                      {formatCurrency(p.price)}
                    </strong>
                    <span className="text-xs text-slate-400">
                      库存 {formatNumber(p.stock)}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1 text-[11px] text-emerald-700">
                    <span className="rounded bg-emerald-50 px-2 py-1">
                      {p.is_returnable ? "支持按规则退货" : "退货条件需核验"}
                    </span>
                    <span className="rounded bg-emerald-50 px-2 py-1">
                      一年有限质保
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
        {!loading && !visible.length && (
          <div className="py-16 text-center">
            <p className="font-medium">没有找到相关商品</p>
            <p className="mt-2 text-sm text-slate-500">
              请调整分类或搜索词后重试
            </p>
          </div>
        )}
      </main>
    </>
  );
}
