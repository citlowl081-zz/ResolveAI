let manifestPromise: Promise<Set<string>> | null = null;

export function availableImages(): Promise<Set<string>> {
  if (!manifestPromise) {
    manifestPromise = fetch("/images/asset-manifest.json")
      .then((response) => (response.ok ? response.json() : { assets: [] }))
      .then(
        (data: { assets?: unknown }) =>
          new Set(
            Array.isArray(data.assets)
              ? data.assets.filter(
                  (item): item is string => typeof item === "string",
                )
              : [],
          ),
      )
      .catch(() => new Set<string>());
  }
  return manifestPromise;
}
