"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "@/lib/navbar";
import { products, type Product } from "@/lib/api";
import { CATEGORIES, CATALOG, catalogByName } from "@/config/catalog";
import { PlannedImage } from "@/components/image-placeholder";
import { formatCurrency } from "@/lib/labels";
const banners = [
  [
    "智能办公焕新季",
    "高效外设，让每一次输入都更从容",
    "/images/banners/banner-01.webp",
  ],
  [
    "沉浸音频体验",
    "专注聆听，也不错过身边世界",
    "/images/banners/banner-02.webp",
  ],
  [
    "桌面效率升级",
    "连接、照明与舒适体验一步到位",
    "/images/banners/banner-03.webp",
  ],
] as const;
function ProductCard({ product }: { product: Product }) {
  const m = catalogByName(product.name);
  return (
    <Link
      href={`/products/${product.id}`}
      className="group overflow-hidden rounded-lg border bg-white shadow-sm hover:-translate-y-0.5 hover:shadow-md"
    >
      <PlannedImage
        src={
          m?.image ||
          product.image_url ||
          "/images/products/unplanned/main.webp"
        }
        alt={`${product.name}主图`}
      />
      <div className="p-3 sm:p-4">
        <p className="text-xs font-medium text-blue-600">
          {CATEGORIES.find((c) => c.slug === m?.category)?.name || "智能数码"}
        </p>
        <h3 className="mt-1 min-h-12 font-semibold">{product.name}</h3>
        <p className="line-clamp-1 text-sm text-slate-500">
          {m?.sellingPoint || product.description}
        </p>
        <p className="mt-3 text-lg font-bold text-blue-600 sm:text-xl">
          {formatCurrency(product.price)}
        </p>
      </div>
    </Link>
  );
}
export default function Home() {
  const [items, setItems] = useState<Product[]>([]);
  useEffect(() => {
    products
      .listAll()
      .then((all) => setItems(all.filter((p) => catalogByName(p.name))))
      .catch(() => undefined);
  }, []);
  return (
    <div className="min-h-screen">
      <Navbar />
      <main>
        <section className="border-b bg-white">
          <div className="mx-auto max-w-7xl px-5 py-8">
            <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
              <div>
                <p className="text-sm font-semibold text-blue-600">
                  智能数码与桌面办公精选商城
                </p>
                <h1 className="mt-2 text-3xl font-black tracking-tight md:text-5xl">
                  让科技自然融入
                  <br />
                  每一张高效桌面
                </h1>
              </div>
              <Link
                href="/products"
                className="rounded-md bg-slate-900 px-6 py-3 text-center font-medium text-white"
              >
                探索全部商品
              </Link>
            </div>
            <form
              action="/products"
              className="mt-7 flex rounded-lg border bg-slate-50 p-2"
            >
              <span className="m-2" aria-hidden>
                ⌕
              </span>
              <input
                name="q"
                className="min-w-0 flex-1 bg-transparent outline-none"
                placeholder="搜索耳机、键盘、充电设备……"
                aria-label="搜索商品"
              />
              <button className="rounded-md bg-blue-600 px-5 py-2 text-sm text-white">
                搜索
              </button>
            </form>
          </div>
        </section>
        <section className="mx-auto grid max-w-7xl grid-cols-2 gap-3 px-5 py-6 md:grid-cols-3 lg:grid-cols-6">
          {CATEGORIES.map((c) => (
            <Link
              key={c.slug}
              href={`/products?category=${c.slug}`}
              className="rounded-lg border bg-white p-3 text-center hover:border-blue-300"
            >
              <PlannedImage
                src={c.image}
                alt={`${c.name}分类图`}
                className="mb-3 aspect-[3/2] rounded-md"
                size="600 × 400 px"
                compact
              />
              <strong>{c.name}</strong>
              <p className="mt-1 text-xs text-slate-500">{c.description}</p>
            </Link>
          ))}
        </section>
        <section className="mx-auto grid max-w-7xl gap-4 px-5 pb-8 md:grid-cols-3">
          {banners.map(([title, desc, src]) => (
            <div
              key={title}
              className="relative overflow-hidden rounded-lg bg-slate-900 text-white"
            >
              <PlannedImage
                src={src}
                alt={`${title} Banner`}
                className="aspect-[3/1] opacity-30"
                size="1920 × 640 px"
              />
              <div className="absolute inset-0 flex flex-col justify-center p-5">
                <h2 className="text-xl font-bold md:text-2xl">{title}</h2>
                <p className="mt-2 hidden text-sm text-slate-200 sm:block">
                  {desc}
                </p>
              </div>
            </div>
          ))}
        </section>
        <section className="border-y bg-white">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-5 px-5 py-6 text-center md:grid-cols-4">
            {[
              ["正品保障", "严选虚构自有品牌"],
              ["七天无理由", "具体以商品规则及法律规定为准"],
              ["极速退款", "进度透明可追踪"],
              ["AI 售后支持", "政策咨询与服务协助"],
            ].map(([a, b]) => (
              <div key={a}>
                <strong>{a}</strong>
                <p className="mt-1 text-xs text-slate-500">{b}</p>
              </div>
            ))}
          </div>
        </section>
        {["热门商品", "新品推荐", "智能办公专区", "音频设备专区"].map(
          (title, index) => (
            <section key={title} className="mx-auto max-w-7xl px-5 py-9">
              <div className="mb-5 flex items-end justify-between">
                <div>
                  <p className="text-sm font-semibold text-blue-600">
                    ResolveAI 精选
                  </p>
                  <h2 className="text-2xl font-bold">{title}</h2>
                </div>
                <Link href="/products" className="text-sm text-blue-600">
                  查看全部 →
                </Link>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:gap-5 lg:grid-cols-4">
                {items.length
                  ? items
                      .slice(index * 4, index * 4 + 4)
                      .map((p) => <ProductCard key={p.id} product={p} />)
                  : CATALOG.slice(index * 4, index * 4 + 4).map((p) => (
                      <div
                        key={p.sku}
                        className="overflow-hidden rounded-lg border bg-white"
                      >
                        <PlannedImage src={p.image} alt={`${p.name}主图`} />
                        <div className="p-4">
                          <p className="font-semibold">{p.name}</p>
                          <p className="mt-1 text-sm text-slate-500">
                            {p.sellingPoint}
                          </p>
                        </div>
                      </div>
                    ))}
              </div>
            </section>
          ),
        )}
        <section className="bg-blue-700 text-white">
          <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-5 px-5 py-12 md:flex-row md:items-center">
            <div>
              <h2 className="text-3xl font-bold">售后问题，先问 AI 助手</h2>
              <p className="mt-2 text-blue-100">
                查询政策、物流与申请条件；写操作始终由你确认。
              </p>
            </div>
            <Link
              href="/agent"
              className="rounded-md bg-white px-6 py-3 font-semibold text-blue-700"
            >
              进入 AI 售后助手
            </Link>
          </div>
        </section>
      </main>
      <footer className="bg-slate-950 px-5 py-10 text-center text-sm text-slate-400">
        <p className="font-semibold text-white">ResolveAI 智选商城</p>
        <p className="mt-2">
          智能数码与桌面办公精选商城 · 演示项目，商品与品牌均为虚构
        </p>
      </footer>
    </div>
  );
}
