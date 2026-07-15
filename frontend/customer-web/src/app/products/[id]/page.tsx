"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Navbar from "@/lib/navbar";
import { products, type Product } from "@/lib/api";

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    products.get(id).then(r => {
      if (r.success && r.data) setProduct(r.data);
    }).finally(() => setLoading(false));
  }, [id]);

  return (
    <div>
      <Navbar />
      <main className="max-w-2xl mx-auto p-6">
        {loading && <p className="text-gray-500">加载中...</p>}
        {product && (
          <div className="bg-white rounded-xl border p-6">
            <h1 className="text-2xl font-bold">{product.name}</h1>
            <div className="mt-4 space-y-2 text-sm text-gray-600">
              <p>分类: {product.category}</p>
              <p className="text-2xl font-bold text-blue-600">¥{product.price}</p>
              <p>库存: {product.stock}</p>
              <p>{product.is_returnable ? "支持退换" : "不可退换"}</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
