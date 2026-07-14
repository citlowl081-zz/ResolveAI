# ResolveAI 微信小程序

基于微信原生框架的客户自助售后小程序，与 ResolveAI Backend API 共用后端服务。

## 目录结构

```
miniprogram/
├── README.md                         # 本文件
├── miniprogram/
│   ├── pages/                        # 页面目录
│   │   └── .gitkeep
│   ├── components/                   # 公共组件
│   │   └── .gitkeep
│   ├── services/                     # API 调用封装
│   │   └── .gitkeep
│   ├── utils/                        # 工具函数
│   │   └── .gitkeep
│   └── assets/                       # 静态资源
│       └── .gitkeep
├── typings/                          # TypeScript 类型声明
│   └── .gitkeep
└── project.config.example.json       # 项目配置模板
```

## 技术栈

- 微信原生小程序框架
- TypeScript（推荐）
- 与 Backend API 通过 HTTPS 通信

## 开发状态

**Phase 03 阶段仅建立基础目录结构。**

小程序功能开发计划在 Phase 07（前端）实施。

## 环境要求

- 微信开发者工具（最新稳定版）
- 微信小程序 AppID
- 后端服务运行中（`docker-compose up -d`）

## 配置

1. 复制项目配置模板：
```bash
cp project.config.example.json project.config.json
```

2. 编辑 `project.config.json`，填入真实 AppID。

3. API 地址配置在 `miniprogram/services/api.ts` 中（待实现）。

## 注意事项

- `project.config.json` 和 `project.private.config.json` 已加入 `.gitignore`，不会提交。
- 微信开发者工具本地缓存和临时文件已忽略。
- 小程序与 Web 前端共用 Backend API，无需独立后端。
