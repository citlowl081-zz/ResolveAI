import { api } from "../../services/api";
import { CATALOG_CATEGORIES, enrichProduct } from "../../utils/catalog";

Page({
  data: {
    items: [] as CatalogProduct[], allItems: [] as CatalogProduct[],
    categories: CATALOG_CATEGORIES, activeCategory: "", query: "", loading: true, error: "",
  },
  async onLoad(options: Record<string, string>) {
    const activeCategory = options.category || "";
    const query = decodeURIComponent(options.q || "");
    this.setData({ activeCategory, query });
    try {
      const res = await api.products.list();
      const allItems = (res.data.data?.items || []).map(enrichProduct);
      this.setData({ allItems });
      this.applyFilters(allItems, activeCategory, query);
    } catch (error) { this.setData({ error: (error as Error).message }); }
    finally { this.setData({ loading: false }); }
  },
  chooseCategory(event: WechatMiniprogram.TouchEvent) {
    const category = event.currentTarget.dataset.category as string;
    this.setData({ activeCategory: category });
    this.applyFilters(this.data.allItems, category, this.data.query);
  },
  applyFilters(items: CatalogProduct[], category: string, query: string) {
    const normalized = query.trim().toLowerCase();
    this.setData({ items: items.filter((item) =>
      (!category || item.categoryKey === category)
      && (!normalized || `${item.name} ${item.description || ""}`.toLowerCase().includes(normalized)),
    ) });
  },
});
