"use client";
import { useState, useEffect } from "react";
import Navbar from "@/lib/navbar";
import { memories, type UserMemory } from "@/lib/api";

export default function MemoriesPage() {
  const [items, setItems] = useState<UserMemory[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [type, setType] = useState("PREFERENCE");
  const [content, setContent] = useState("");
  const [key, setKey] = useState("");

  async function load() {
    setLoading(true);
    try {
      const r = await memories.list();
      if (r.success && r.data) setItems(r.data.items);
    } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function create() {
    if (!content.trim()) return;
    try {
      await memories.create({ memory_type: type, content, key: key || undefined });
      setContent(""); setKey(""); setCreating(false);
      load();
    } catch (e: unknown) { alert(e instanceof Error ? e.message : "创建失败"); }
  }

  async function remove(id: string) {
    try { await memories.delete(id); load(); } catch (e: unknown) { alert(e instanceof Error ? e.message : "删除失败"); }
  }

  return (
    <div>
      <Navbar />
      <main className="max-w-4xl mx-auto p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">我的记忆</h1>
          <button onClick={() => setCreating(!creating)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">{creating ? "取消" : "新建"}</button>
        </div>
        {creating && (
          <div className="bg-white border rounded-lg p-4 mb-6 space-y-3">
            <select value={type} onChange={e => setType(e.target.value)} className="w-full px-3 py-2 border rounded">
              <option value="PREFERENCE">偏好 (PREFERENCE)</option>
              <option value="FACT">事实 (FACT)</option>
              <option value="SUMMARY">摘要 (SUMMARY)</option>
            </select>
            <input placeholder="Key (可选, 用于去重)" value={key} onChange={e => setKey(e.target.value)} className="w-full px-3 py-2 border rounded" />
            <textarea placeholder="内容" value={content} onChange={e => setContent(e.target.value)} rows={3} className="w-full px-3 py-2 border rounded" />
            <button onClick={create} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm">保存</button>
          </div>
        )}
        {loading && <p className="text-gray-500">加载中...</p>}
        <div className="space-y-3">
          {items.map(m => (
            <div key={m.id} className="p-4 bg-white rounded-lg border flex justify-between items-start">
              <div>
                <div className="flex gap-2 items-center mb-1">
                  <span className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700">{m.memory_type}</span>
                  {m.key && <span className="text-xs text-gray-400 font-mono">{m.key}</span>}
                  <span className="text-xs text-gray-400">v{m.version}</span>
                </div>
                <p className="text-sm">{m.content}</p>
                <p className="text-xs text-gray-400 mt-1">来源: {m.source} | 置信度: {(m.confidence * 100).toFixed(0)}%</p>
              </div>
              <button onClick={() => remove(m.id)} className="text-red-400 hover:text-red-600 text-sm">删除</button>
            </div>
          ))}
        </div>
        {!loading && items.length === 0 && <p className="text-gray-400">暂无记忆</p>}
      </main>
    </div>
  );
}
