"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminProducts, type Product } from "@/lib/api";
import { productMeta } from "@/lib/catalog";
import { ProductImage } from "@/components/image-placeholder";
import { formatCurrency, formatNumber } from "@/lib/labels";
export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const [p, setP] = useState<Product | null>(null);
  useEffect(() => {
    adminProducts.get(id).then((r) => setP(r.data));
  }, [id]);
  if (!p) return <p className="p-8">正在加载商品详情…</p>;
  const m = productMeta(p.name, p.category);
  return (
    <main className="p-5 md:p-8">
      <h1 className="text-3xl font-bold">商品详情</h1>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <section className="rounded-lg border bg-white p-6">
          <h2 className="font-bold">图片资源状态</h2>
          <ProductImage
            src={`/images/products/${m.slug}/main.webp`}
            alt={p.name}
          />
          <p className="mt-3 text-sm text-slate-500">
            主图路径：/images/products/{m.slug}/main.webp
          </p>
        </section>
        <section className="rounded-lg border bg-white p-6 lg:col-span-2">
          <h2 className="font-bold">商品基本信息</h2>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-slate-500">商品名称</dt>
              <dd className="font-medium">{p.name}</dd>
            </div>
            <div>
              <dt className="text-slate-500">SKU</dt>
              <dd>{m.sku}</dd>
            </div>
            <div>
              <dt className="text-slate-500">类目</dt>
              <dd>{m.category}</dd>
            </div>
            <div>
              <dt className="text-slate-500">售价</dt>
              <dd>{formatCurrency(p.price)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">库存</dt>
              <dd>{formatNumber(p.stock)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">状态</dt>
              <dd>在售</dd>
            </div>
          </dl>
          <h2 className="mt-8 font-bold">售后规则</h2>
          <p className="mt-2 rounded-xl bg-blue-50 p-4 text-sm">
            {m.afterSales}。质量问题、物流破损和一年有限质保按对应政策处理。
          </p>
        </section>
      </div>
      <section className="mt-6 grid gap-4 md:grid-cols-3">
        {["关联订单与工单", "退货率与换货率", "质量问题率"].map((x) => (
          <div key={x} className="rounded-lg border bg-white p-5">
            <h2 className="font-bold">{x}</h2>
            <p className="mt-3 text-slate-400">暂无统计数据</p>
          </div>
        ))}
      </section>
    </main>
  );
}
