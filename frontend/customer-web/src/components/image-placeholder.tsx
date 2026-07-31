"use client";
/* eslint-disable @next/next/no-img-element -- Native load/error events are required for zero-code static asset replacement. */
import { useEffect, useState } from "react";
import { availableImages } from "@/lib/image-manifest";

export function ImagePlaceholder({
  label = "待上传商品主图",
  size = "800 × 800 px",
  fileName,
  compact = false,
}: {
  label?: string;
  size?: string;
  fileName: string;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex h-full w-full flex-col items-center justify-center border-2 border-dashed border-slate-300 bg-slate-100 text-center text-slate-500 ${compact ? "p-2 text-[10px]" : "p-6 text-sm"}`}
    >
      <span className={compact ? "text-xl" : "text-3xl"} aria-hidden>
        ▧
      </span>
      <strong className="mt-2 text-slate-600">{label}</strong>
      <span>建议尺寸：{size}</span>
      {!compact && <span className="mt-1 break-all">文件名：{fileName}</span>}
    </div>
  );
}

export function PlannedImage({
  src,
  alt,
  className = "aspect-square",
  size = "800 × 800 px",
  compact = false,
}: {
  src: string;
  alt: string;
  className?: string;
  size?: string;
  compact?: boolean;
}) {
  const [loaded, setLoaded] = useState(false);
  const [available, setAvailable] = useState(false);
  useEffect(() => {
    let active = true;
    availableImages().then((assets) => {
      if (active) setAvailable(assets.has(src));
    });
    return () => {
      active = false;
    };
  }, [src]);
  const fileName = src.split("/").pop() || src;
  return (
    <div className={`relative overflow-hidden ${className}`}>
      {!loaded && (
        <ImagePlaceholder
          label={`待上传${alt}`}
          size={size}
          fileName={fileName}
          compact={compact}
        />
      )}
      {available && (
        <img
          src={src}
          alt={alt}
          className={`absolute inset-0 h-full w-full object-cover ${loaded ? "block" : "hidden"}`}
          onLoad={() => setLoaded(true)}
          onError={() => setAvailable(false)}
        />
      )}
    </div>
  );
}
