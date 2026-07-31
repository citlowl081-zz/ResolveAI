export interface CatalogCategory {
  key: string;
  label: string;
  icon: string;
  keywords: string[];
}

export const CATALOG_CATEGORIES: CatalogCategory[] = [
  { key: "audio", label: "音频设备", icon: "音", keywords: ["耳机", "音箱", "麦克风"] },
  { key: "computer", label: "电脑外设", icon: "键", keywords: ["键盘", "鼠标", "显示器", "摄像头"] },
  { key: "mobile", label: "移动配件", icon: "充", keywords: ["充电", "数据线", "移动电源", "手机支架"] },
  { key: "office", label: "桌面办公", icon: "桌", keywords: ["桌", "椅", "灯", "收纳"] },
  { key: "wearable", label: "智能穿戴", icon: "表", keywords: ["手表", "手环"] },
  { key: "home", label: "智能家居", icon: "家", keywords: ["智能", "插座", "灯泡", "门锁"] },
];

export function enrichProduct(product: Product): CatalogProduct {
  const category = CATALOG_CATEGORIES.find((item) =>
    item.keywords.some((keyword) => product.name.includes(keyword)),
  ) || CATALOG_CATEGORIES[1];
  return { ...product, categoryKey: category.key, categoryLabel: category.label };
}
