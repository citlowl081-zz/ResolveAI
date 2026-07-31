"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import Navbar from "@/lib/navbar";
import { products, type Product } from "@/lib/api";
import { catalogByName, categoryBySlug } from "@/config/catalog";
import { PlannedImage } from "@/components/image-placeholder";
import { formatCurrency, formatNumber, friendlyError } from "@/lib/labels";
export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<Product | null>(null),
    [all, setAll] = useState<Product[]>([]),
    [error, setError] = useState("");
  useEffect(() => {
    products
      .get(id)
      .then((r) => setProduct(r.data))
      .catch((e) => setError(friendlyError(e)));
    products
      .listAll()
      .then(setAll)
      .catch(() => undefined);
  }, [id]);
  const m = product ? catalogByName(product.name) : undefined;
  const related = useMemo(
    () =>
      all
        .filter(
          (p) => p.id !== id && catalogByName(p.name)?.category === m?.category,
        )
        .slice(0, 3),
    [all, id, m?.category],
  );
  if (error)
    return (
      <>
        <Navbar />
        <p className="p-16 text-center text-red-600">{error}</p>
      </>
    );
  if (!product)
    return (
      <>
        <Navbar />
        <p className="p-16 text-center text-slate-500">正在加载商品详情…</p>
      </>
    );
  const category = categoryBySlug(m?.category || "");
  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-6xl p-5 md:p-8">
        <div className="grid gap-8 md:grid-cols-2">
          <div>
            <PlannedImage
              src={
                m?.image ||
                product.image_url ||
                "/images/products/unplanned/main.webp"
              }
              alt={`${product.name}主图`}
              className="aspect-square rounded-lg"
            />
            <div className="mt-3 grid grid-cols-3 gap-3">
              {[1, 2, 3].map((n) => (
                <PlannedImage
                  key={n}
                  src={`/images/products/${m?.slug || "unplanned"}/detail-0${n}.webp`}
                  alt={`${product.name}详情图 ${n}`}
                  className="aspect-[4/3] rounded-md"
                  size="1200 × 900 px"
                  compact
                />
              ))}
            </div>
          </div>
          <div className="py-2">
            <p className="font-semibold text-blue-600">
              {category?.name || "智能数码"}
            </p>
            <h1 className="mt-2 text-3xl font-black">{product.name}</h1>
            <p className="mt-3 text-slate-500">{product.description}</p>
            <ul className="mt-5 space-y-2 text-sm">
              {(
                m?.sellingPoints || [
                  product.description || "精选智能数码产品",
                  "具体参数以商品说明为准",
                ]
              ).map((x) => (
                <li key={x} className="flex gap-2">
                  <span className="text-emerald-600">✓</span>
                  {x}
                </li>
              ))}
            </ul>
            <p className="mt-7 text-4xl font-black text-blue-600">
              {formatCurrency(product.price)}
            </p>
            <dl className="mt-6 grid grid-cols-2 gap-4 rounded-lg bg-slate-50 p-5 text-sm">
              <div>
                <dt className="text-slate-500">商品编号</dt>
                <dd className="mt-1 font-semibold">{m?.sku || "演示商品"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">库存数量</dt>
                <dd className="mt-1 font-semibold">
                  {formatNumber(product.stock)} 件
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">质保期限</dt>
                <dd className="mt-1 font-semibold">
                  {m?.warranty || "一年有限质保"}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">商品状态</dt>
                <dd className="mt-1 font-semibold">
                  {product.stock > 0 ? "在售" : "暂时缺货"}
                </dd>
              </div>
            </dl>
            <Link
              href={`/agent?product=${encodeURIComponent(product.name)}`}
              className="mt-6 block w-full rounded-md bg-slate-900 py-3 text-center font-semibold text-white"
            >
              咨询 AI 售后助手
            </Link>
          </div>
        </div>
        <section className="mt-12 rounded-lg border bg-white p-6 md:p-8">
          <h2 className="text-2xl font-bold">售后保障</h2>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["七天无理由", "拆封与合理试用不当然影响商品完好"],
              ["质量问题退换", "经核验后按生效政策处理"],
              ["物流破损保障", "签收异常可提交凭证"],
              ["一年有限质保", m?.warranty || "具体以商品说明为准"],
            ].map(([a, b]) => (
              <div
                key={a}
                className="rounded-lg border border-blue-100 bg-blue-50 p-4"
              >
                <strong>{a}</strong>
                <p className="mt-1 text-sm text-slate-600">{b}</p>
              </div>
            ))}
          </div>
          <p className="mt-5 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">
            {m?.afterSales || "具体以商品售后政策和法律规定为准。"}
          </p>
          <p className="mt-3 text-xs text-slate-500">
            法律规则与 ResolveAI
            平台运营规则分别适用；特殊排除品类、激活绑定或卫生属性需结合商品实际状态单独判断。
          </p>
        </section>
        <section className="mt-8 grid gap-5 md:grid-cols-2">
          <div className="rounded-lg border bg-white p-6">
            <h2 className="text-xl font-bold">相关政策</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              政策以知识库中当前生效版本为准。可通过 AI 售后助手检索真实 Policy
              Key、标题、版本与引用内容。
            </p>
            <Link
              href="/agent"
              className="mt-4 inline-block text-sm font-medium text-blue-600"
            >
              查询适用政策 →
            </Link>
          </div>
          <div className="rounded-lg border bg-white p-6">
            <h2 className="text-xl font-bold">商品参数</h2>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">类目</dt>
                <dd>{category?.name || "智能数码"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">是否可退</dt>
                <dd>
                  {product.is_returnable ? "支持按规则申请" : "需单独核验"}
                </dd>
              </div>
            </dl>
          </div>
        </section>
        {related.length > 0 && (
          <section className="mt-9">
            <h2 className="text-2xl font-bold">相关推荐</h2>
            <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-3">
              {related.map((p) => {
                const r = catalogByName(p.name);
                return (
                  <Link
                    key={p.id}
                    href={`/products/${p.id}`}
                    className="overflow-hidden rounded-lg border bg-white"
                  >
                    <PlannedImage
                      src={r?.image || "/images/products/unplanned/main.webp"}
                      alt={`${p.name}主图`}
                      compact
                    />
                    <div className="p-3">
                      <p className="font-medium">{p.name}</p>
                      <p className="mt-1 text-blue-600">
                        {formatCurrency(p.price)}
                      </p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        )}
      </main>
    </>
  );
}
