export type CatalogCategory = { slug: string; name: string; description: string; image: string };
export type CatalogProduct = {
  slug: string; name: string; sku: string; category: string; image: string;
  sellingPoint: string; sellingPoints: string[]; warranty: string; afterSales: string;
};

export const CATEGORIES: CatalogCategory[] = [
  { slug: "audio", name: "音频设备", description: "沉浸聆听与清晰沟通", image: "/images/categories/audio.webp" },
  { slug: "peripherals", name: "电脑外设", description: "提升输入与连接效率", image: "/images/categories/peripherals.webp" },
  { slug: "mobile-accessories", name: "移动配件", description: "高效充电与便捷出行", image: "/images/categories/mobile-accessories.webp" },
  { slug: "desktop-office", name: "桌面办公", description: "舒适、整洁、高效桌面", image: "/images/categories/desktop-office.webp" },
  { slug: "wearables", name: "智能穿戴", description: "关注运动与生活趋势", image: "/images/categories/wearables.webp" },
  { slug: "smart-home", name: "智能家居", description: "便捷可靠的智能空间", image: "/images/categories/smart-home.webp" },
];

const rows = [
  ["aurora-buds-pro", "Aurora Buds Pro 无线降噪耳机", "RA-AUD-001", "audio", "自适应降噪，通勤办公更专注"],
  ["sonic-air", "Sonic Air 开放式蓝牙耳机", "RA-AUD-002", "audio", "开放聆听，舒适感知环境"],
  ["studio-one", "Studio One 桌面监听音箱", "RA-AUD-003", "audio", "紧凑桌面，细腻立体声"],
  ["voicelink", "VoiceLink USB 麦克风", "RA-AUD-004", "audio", "即插即用，会议创作更清晰"],
  ["flowkeys", "FlowKeys 机械键盘", "RA-PER-001", "peripherals", "多设备切换，畅快输入"],
  ["glide-pro", "Glide Pro 无线鼠标", "RA-PER-002", "peripherals", "轻量双模，精准顺滑"],
  ["visionbar", "VisionBar 2K 摄像头", "RA-PER-003", "peripherals", "2K 画质，远程会议更自然"],
  ["dockmate", "DockMate 12 合 1 扩展坞", "RA-PER-004", "peripherals", "一线扩展，释放桌面潜力"],
  ["powercube", "PowerCube 65W 氮化镓充电器", "RA-MOB-001", "mobile-accessories", "小巧三口，差旅快充"],
  ["magflow", "MagFlow 磁吸无线充电座", "RA-MOB-002", "mobile-accessories", "立式磁吸，随放随充"],
  ["flexline", "FlexLine 编织数据线", "RA-MOB-003", "mobile-accessories", "耐弯折，快充与传输兼备"],
  ["travelhub", "TravelHub 移动电源", "RA-MOB-004", "mobile-accessories", "双向快充，电量清晰可见"],
  ["halo-monitor", "Halo Monitor 智能屏幕挂灯", "RA-OFF-001", "desktop-office", "减少反光，专注桌面照明"],
  ["ergolift", "ErgoLift 笔记本支架", "RA-OFF-002", "desktop-office", "多档抬升，舒适办公"],
  ["deskflow", "DeskFlow 智能插座", "RA-OFF-003", "desktop-office", "定时控制，管理桌面用电"],
  ["quietdesk", "QuietDesk 桌面静音风扇", "RA-OFF-004", "desktop-office", "安静送风，清爽工作"],
  ["pulse-watch", "Pulse Watch 智能手表", "RA-WEA-001", "wearables", "全天趋势与运动记录"],
  ["motion-band", "Motion Band 健身手环", "RA-WEA-002", "wearables", "轻量长续航，活力随行"],
  ["sleep-ring", "Sleep Ring 睡眠监测指环", "RA-WEA-003", "wearables", "无屏轻巧，记录睡眠趋势"],
  ["homesense", "HomeSense 智能网关", "RA-HOM-001", "smart-home", "连接设备，构建自动化场景"],
  ["airguard", "AirGuard 空气质量传感器", "RA-HOM-002", "smart-home", "掌握空间环境变化"],
  ["lightcore", "LightCore 智能氛围灯", "RA-HOM-003", "smart-home", "多场景灯光，点亮桌面"],
  ["secureeye", "SecureEye 室内智能摄像头", "RA-HOM-004", "smart-home", "移动侦测与隐私遮蔽"],
] as const;

export const CATALOG: CatalogProduct[] = rows.map(([slug, name, sku, category, sellingPoint]) => ({
  slug, name, sku, category, sellingPoint,
  sellingPoints: [sellingPoint, category === "audio" ? "低延迟连接与清晰通话，兼顾办公和日常使用" : category === "desktop-office" ? "简洁设计融入桌面，兼顾可靠性与使用效率" : "稳定连接与易用设计，满足日常多场景需求"],
  image: `/images/products/${slug}/main.webp`,
  warranty: "一年有限质保",
  afterSales: category === "audio"
    ? "支持依法判断七天无理由退货。拆封和合理试用不当然影响商品完好；涉及卫生、激活绑定等情形需按具体商品状态核验。"
    : "支持七天无理由与质量问题退换，具体以商品完好情况、售后政策及法律规定为准。",
}));

export const catalogByName = (name: string) => CATALOG.find(item => item.name === name);
export const categoryBySlug = (slug: string) => CATEGORIES.find(item => item.slug === slug);
