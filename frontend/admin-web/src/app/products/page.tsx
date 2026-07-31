"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { adminProducts, type Product } from "@/lib/api";
import { PRODUCT_META, productMeta } from "@/lib/catalog";
import { ProductImage } from "@/components/image-placeholder";
import { formatCurrency, formatNumber } from "@/lib/labels";

export default function ProductsPage() {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    adminProducts
      .listAll()
      .then((all) => setItems(all.filter((p) => PRODUCT_META[p.name])))
      .finally(() => setLoading(false));
  }, []);
  return (
    <main className="p-5 md:p-8">
      <div>
        <p className="text-sm font-semibold text-blue-600">商品中心</p>
        <h1 className="text-3xl font-bold">商品管理</h1>
        <p className="mt-2 text-slate-500">智能数码与桌面办公商品目录</p>
      </div>
      {loading && <p className="py-12 text-center">正在加载商品…</p>}
      <div className="mt-6 overflow-x-auto rounded-lg border bg-white">
        <table className="w-full min-w-[1050px] text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              {[
                "商品图片",
                "商品名称",
                "SKU",
                "类目",
                "售价",
                "库存",
                "销量",
                "售后政策",
                "商品状态",
                "更新时间",
                "操作",
              ].map((h) => (
                <th key={h} className="p-3">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((p) => {
              const m = productMeta(p.name, p.category);
              return (
                <tr key={p.id} className="border-t">
                  <td className="p-3">
                    <ProductImage
                      src={`/images/products/${m.slug}/main.webp`}
                      alt={p.name}
                      compact
                    />
                  </td>
                  <td className="p-3 font-medium">{p.name}</td>
                  <td className="p-3 font-mono text-xs">{m.sku}</td>
                  <td className="p-3">{m.category}</td>
                  <td className="p-3">{formatCurrency(p.price)}</td>
                  <td className="p-3">{formatNumber(p.stock)}</td>
                  <td className="p-3 text-slate-400">暂无统计数据</td>
                  <td className="max-w-48 p-3 text-xs">{m.afterSales}</td>
                  <td className="p-3">
                    <span className="rounded-full bg-green-50 px-2 py-1 text-green-700">
                      在售
                    </span>
                  </td>
                  <td className="p-3 text-slate-400">—</td>
                  <td className="p-3">
                    <Link className="text-blue-600" href={`/products/${p.id}`}>
                      查看详情
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </main>
  );
}
