"use client";
/* eslint-disable @next/next/no-img-element -- Native load/error events are required for zero-code static asset replacement. */
import { useEffect, useState } from "react";
import { availableImages } from "@/lib/image-manifest";
export function ProductImage({
  src,
  alt,
  compact = false,
}: {
  src: string;
  alt: string;
  compact?: boolean;
}) {
  const [ok, setOk] = useState(false);
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
  return (
    <div
      className={`relative flex shrink-0 items-center justify-center overflow-hidden border-2 border-dashed border-slate-300 bg-slate-100 text-center text-slate-500 ${compact ? "h-14 w-14 text-[9px]" : "aspect-square w-full text-sm"}`}
    >
      {!ok && (
        <span>
          ▧<br />
          待上传
          <br />
          建议 800×800
        </span>
      )}
      {available && (
        <img
          src={src}
          alt={alt}
          className={`absolute inset-0 h-full w-full object-cover ${ok ? "block" : "hidden"}`}
          onLoad={() => setOk(true)}
          onError={() => setAvailable(false)}
        />
      )}
    </div>
  );
}
