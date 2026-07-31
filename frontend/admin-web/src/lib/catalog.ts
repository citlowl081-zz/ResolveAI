export const PRODUCT_META: Record<
  string,
  { sku: string; category: string; slug: string; afterSales: string }
> = {
  "Aurora Buds Pro 无线降噪耳机": {
    sku: "RA-AUD-001",
    category: "音频设备",
    slug: "aurora-buds-pro",
    afterSales: "拆封与合理试用不当然影响商品完好，按商品状态及政策核验",
  },
  "Sonic Air 开放式蓝牙耳机": {
    sku: "RA-AUD-002",
    category: "音频设备",
    slug: "sonic-air",
    afterSales: "七天无理由与质量问题退换",
  },
  "Studio One 桌面监听音箱": {
    sku: "RA-AUD-003",
    category: "音频设备",
    slug: "studio-one",
    afterSales: "七天无理由与一年有限质保",
  },
  "VoiceLink USB 麦克风": {
    sku: "RA-AUD-004",
    category: "音频设备",
    slug: "voicelink",
    afterSales: "七天无理由与一年有限质保",
  },
  "FlowKeys 机械键盘": {
    sku: "RA-PER-001",
    category: "电脑外设",
    slug: "flowkeys",
    afterSales: "七天无理由与一年有限质保",
  },
  "Glide Pro 无线鼠标": {
    sku: "RA-PER-002",
    category: "电脑外设",
    slug: "glide-pro",
    afterSales: "七天无理由与一年有限质保",
  },
  "VisionBar 2K 摄像头": {
    sku: "RA-PER-003",
    category: "电脑外设",
    slug: "visionbar",
    afterSales: "七天无理由与一年有限质保",
  },
  "DockMate 12 合 1 扩展坞": {
    sku: "RA-PER-004",
    category: "电脑外设",
    slug: "dockmate",
    afterSales: "七天无理由与一年有限质保",
  },
  "PowerCube 65W 氮化镓充电器": {
    sku: "RA-MOB-001",
    category: "移动配件",
    slug: "powercube",
    afterSales: "七天无理由与一年有限质保",
  },
  "MagFlow 磁吸无线充电座": {
    sku: "RA-MOB-002",
    category: "移动配件",
    slug: "magflow",
    afterSales: "七天无理由与一年有限质保",
  },
  "FlexLine 编织数据线": {
    sku: "RA-MOB-003",
    category: "移动配件",
    slug: "flexline",
    afterSales: "七天无理由与一年有限质保",
  },
  "TravelHub 移动电源": {
    sku: "RA-MOB-004",
    category: "移动配件",
    slug: "travelhub",
    afterSales: "七天无理由与一年有限质保",
  },
  "Halo Monitor 智能屏幕挂灯": {
    sku: "RA-OFF-001",
    category: "桌面办公",
    slug: "halo-monitor",
    afterSales: "七天无理由与一年有限质保",
  },
  "ErgoLift 笔记本支架": {
    sku: "RA-OFF-002",
    category: "桌面办公",
    slug: "ergolift",
    afterSales: "七天无理由与一年有限质保",
  },
  "DeskFlow 智能插座": {
    sku: "RA-OFF-003",
    category: "桌面办公",
    slug: "deskflow",
    afterSales: "七天无理由与一年有限质保",
  },
  "QuietDesk 桌面静音风扇": {
    sku: "RA-OFF-004",
    category: "桌面办公",
    slug: "quietdesk",
    afterSales: "七天无理由与一年有限质保",
  },
  "Pulse Watch 智能手表": {
    sku: "RA-WEA-001",
    category: "智能穿戴",
    slug: "pulse-watch",
    afterSales: "激活绑定状态需核验；质量问题享有限质保",
  },
  "Motion Band 健身手环": {
    sku: "RA-WEA-002",
    category: "智能穿戴",
    slug: "motion-band",
    afterSales: "激活绑定状态需核验；质量问题享有限质保",
  },
  "Sleep Ring 睡眠监测指环": {
    sku: "RA-WEA-003",
    category: "智能穿戴",
    slug: "sleep-ring",
    afterSales: "涉及贴身使用与卫生属性时需单独核验",
  },
  "HomeSense 智能网关": {
    sku: "RA-HOM-001",
    category: "智能家居",
    slug: "homesense",
    afterSales: "七天无理由与一年有限质保",
  },
  "AirGuard 空气质量传感器": {
    sku: "RA-HOM-002",
    category: "智能家居",
    slug: "airguard",
    afterSales: "七天无理由与一年有限质保",
  },
  "LightCore 智能氛围灯": {
    sku: "RA-HOM-003",
    category: "智能家居",
    slug: "lightcore",
    afterSales: "七天无理由与一年有限质保",
  },
  "SecureEye 室内智能摄像头": {
    sku: "RA-HOM-004",
    category: "智能家居",
    slug: "secureeye",
    afterSales: "解绑与数据清除后按商品状态核验",
  },
};

const categoryFallback: Record<string, string> = {
  ELECTRONICS: "智能数码",
  HOME: "桌面办公",
};
export function productMeta(name: string, rawCategory: string) {
  return (
    PRODUCT_META[name] || {
      sku: "RA-DEMO",
      category: categoryFallback[rawCategory] || "智能数码",
      slug: "unplanned",
      afterSales: "以商品政策及法律规定为准",
    }
  );
}
