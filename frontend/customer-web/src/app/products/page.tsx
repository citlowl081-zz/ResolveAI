"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import Navbar from "@/lib/navbar";
import { products, type Product } from "@/lib/api";

export default function ProductsPage() {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    products.list().then(r => {
      if (r.success && r.data) setItems(r.data.items);
    }).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <Navbar />
      <main className="max-w-4xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">商品列表</h1>
        {loading && <p className="text-gray-500">加载中...</p>}
        {error && <p className="text-red-500">{error}</p>}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map(p => (
            <Link key={p.id} href={`/products/${p.id}`} className="p-4 bg-white rounded-lg border hover:shadow-md transition-all">
              <h3 className="font-semibold">{p.name}</h3>
              <p className="text-sm text-gray-500">{p.category}</p>
              <p className="text-lg font-bold text-blue-600 mt-2">¥{p.price}</p>
              <p className="text-xs text-gray-400">库存: {p.stock}</p>
            </Link>
          ))}
        </div>
        {!loading && items.length === 0 && <p className="text-gray-400">暂无商品</p>}
      </main>
    </div>
  );
}
