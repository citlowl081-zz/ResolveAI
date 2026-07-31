import { mkdir, readdir, writeFile } from "node:fs/promises";
import { extname, join, relative, sep } from "node:path";

const root = join(process.cwd(), "public", "images");
const manifestPath = join(root, "asset-manifest.json");
const allowed = new Set([".webp", ".png", ".jpg", ".jpeg", ".svg"]);

async function collect(directory) {
  const entries = await readdir(directory, { withFileTypes: true }).catch(
    () => [],
  );
  const paths = [];
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) paths.push(...(await collect(path)));
    else if (allowed.has(extname(entry.name).toLowerCase()))
      paths.push(`/images/${relative(root, path).split(sep).join("/")}`);
  }
  return paths;
}

await mkdir(root, { recursive: true });
await writeFile(
  manifestPath,
  `${JSON.stringify({ assets: (await collect(root)).sort() }, null, 2)}\n`,
);
