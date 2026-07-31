# ResolveAI 图片资产准备指南

当前仓库不包含商品摄影图，也不使用网络图片。图片缺失时页面显示固定比例的 `ImagePlaceholder`，不显示浏览器损坏图标，也不会请求清单中不存在的图片路径。用户只需按下表准备文件并放入对应 `public` 目录，无需修改代码；启动开发服务或构建镜像时会自动生成资源清单。

## 通用资产

| 使用位置 | 推荐尺寸 | 格式 | 文件路径 | 是否必需 | 当前状态 | 内容建议 |
|---|---:|---|---|---|---|---|
| 用户商城 Logo | 自适应矢量 | SVG | `frontend/customer-web/public/images/brand/logo.svg` | 否 | RA 字母占位 | 简洁 RA 字母图形与 ResolveAI 字标 |
| 管理后台 Logo | 自适应矢量 | SVG | `frontend/admin-web/public/images/brand/logo.svg` | 否 | RA 字母占位 | 与商城一致的单色版本 |
| 首页 Banner 1 | 1920×640 | WebP | `frontend/customer-web/public/images/banners/banner-01.webp` | 否 | 待上传 | 智能办公焕新季，留出文字安全区 |
| 首页 Banner 2 | 1920×640 | WebP | `frontend/customer-web/public/images/banners/banner-02.webp` | 否 | 待上传 | 沉浸音频体验，避免真实品牌标识 |
| 首页 Banner 3 | 1920×640 | WebP | `frontend/customer-web/public/images/banners/banner-03.webp` | 否 | 待上传 | 桌面效率升级，统一冷色调 |

## 分类图片

| 分类 | 推荐尺寸 | 文件路径 | 当前状态 |
|---|---:|---|---|
| 音频设备 | 600×400 | `/images/categories/audio.webp` | 待上传 |
| 电脑外设 | 600×400 | `/images/categories/peripherals.webp` | 待上传 |
| 移动配件 | 600×400 | `/images/categories/mobile-accessories.webp` | 待上传 |
| 桌面办公 | 600×400 | `/images/categories/desktop-office.webp` | 待上传 |
| 智能穿戴 | 600×400 | `/images/categories/wearables.webp` | 待上传 |
| 智能家居 | 600×400 | `/images/categories/smart-home.webp` | 待上传 |

## 商品图片完整清单

每件商品准备 1 张 800×800 WebP 主图和 3 张 1200×900 WebP 详情图。列表缩略图由主图裁剪，不需要重复准备。下表的目录均位于 `frontend/customer-web/public/images/products/`；如需管理后台同时显示实图，将同一目录同步到 `frontend/admin-web/public/images/products/`。

| 商品 | 目录 | 主图（800×800） | 详情图（1200×900） | 当前状态 |
|---|---|---|---|---|
| Aurora Buds Pro 无线降噪耳机 | `aurora-buds-pro/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| Sonic Air 开放式蓝牙耳机 | `sonic-air/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| Studio One 桌面监听音箱 | `studio-one/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| VoiceLink USB 麦克风 | `voicelink/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| FlowKeys 机械键盘 | `flowkeys/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| Glide Pro 无线鼠标 | `glide-pro/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| VisionBar 2K 摄像头 | `visionbar/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| DockMate 12 合 1 扩展坞 | `dockmate/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| PowerCube 65W 氮化镓充电器 | `powercube/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| MagFlow 磁吸无线充电座 | `magflow/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| FlexLine 编织数据线 | `flexline/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| TravelHub 移动电源 | `travelhub/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| Halo Monitor 智能屏幕挂灯 | `halo-monitor/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| ErgoLift 笔记本支架 | `ergolift/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| DeskFlow 智能插座 | `deskflow/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| QuietDesk 桌面静音风扇 | `quietdesk/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| Pulse Watch 智能手表 | `pulse-watch/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| Motion Band 健身手环 | `motion-band/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| Sleep Ring 睡眠监测指环 | `sleep-ring/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| HomeSense 智能网关 | `homesense/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| AirGuard 空气质量传感器 | `airguard/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| LightCore 智能氛围灯 | `lightcore/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |
| SecureEye 室内智能摄像头 | `secureeye/` | `main.webp` | `detail-01.webp`、`detail-02.webp`、`detail-03.webp` | 待上传 |

## 数量与替换步骤

- 唯一图片资产共 **103 个**：Logo 2 个、Banner 3 个、分类图 6 个、商品主图 23 个、商品详情图 69 个。
- 管理后台如需展示商品实图，需要将 23 张商品主图按相同目录复制一份；这不增加唯一设计资产数量。
- 替换步骤：按推荐尺寸导出 WebP/SVG → 使用指定文件名 → 放入对应 `public` 目录 → 重新启动开发服务或构建镜像以自动更新资源清单 → 刷新浏览器。
- 图片内容不得包含未经许可的商标、个人隐私、订单信息或误导性认证标识。
