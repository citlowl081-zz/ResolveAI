#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const projectDir = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const sourceDir = path.join(projectDir, "miniprogram");
const failures = [];

function read(relativePath) {
  return fs.readFileSync(path.join(projectDir, relativePath), "utf8");
}

function fail(message) {
  failures.push(message);
}

let appConfig;
try {
  appConfig = JSON.parse(read("miniprogram/app.json"));
} catch {
  fail("app.json 无法解析");
  appConfig = { pages: [], subPackages: [], tabBar: { list: [] } };
}

const pagePaths = [
  ...(appConfig.pages || []),
  ...(appConfig.subPackages || []).flatMap((item) =>
    (item.pages || []).map((page) => `${item.root}/${page}`),
  ),
];

for (const pagePath of pagePaths) {
  for (const extension of ["ts", "json", "wxml", "wxss"]) {
    if (!fs.existsSync(path.join(sourceDir, `${pagePath}.${extension}`))) {
      fail(`页面四件套缺失：${pagePath}.${extension}`);
    }
  }
  try {
    JSON.parse(fs.readFileSync(path.join(sourceDir, `${pagePath}.json`), "utf8"));
  } catch {
    fail(`页面 JSON 无法解析：${pagePath}.json`);
  }
}

for (const item of appConfig.tabBar?.list || []) {
  if (!(appConfig.pages || []).includes(item.pagePath)) {
    fail(`tabBar 页面不在主包 pages 中：${item.pagePath}`);
  }
  for (const iconField of ["iconPath", "selectedIconPath"]) {
    const iconPath = item[iconField];
    if (typeof iconPath !== "string" || !iconPath) {
      fail(`tabBar ${item.text} 缺少 ${iconField}`);
    } else if (/^https?:\/\//i.test(iconPath)) {
      fail(`tabBar ${item.text} 使用网络图标`);
    } else if (!fs.existsSync(path.join(sourceDir, iconPath))) {
      fail(`tabBar ${item.text} 图标不存在：${iconPath}`);
    }
  }
}

const expectedTabs = [
  ["pages/index/index", "首页"],
  ["pages/agent/agent", "消息"],
  ["pages/cart/cart", "购物车"],
  ["pages/profile/profile", "我的"],
];
const actualTabs = (appConfig.tabBar?.list || []).map((item) => [item.pagePath, item.text]);
if (JSON.stringify(actualTabs) !== JSON.stringify(expectedTabs)) {
  fail("tabBar 必须依次为：首页、消息、购物车、我的");
}

const sourceFiles = [];
function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(fullPath);
    else sourceFiles.push(fullPath);
  }
}
walk(sourceDir);

const navigationPattern = /(?:url|pagePath)\s*[=:]\s*["'`]\/?([^"'`?]+)/g;
for (const filePath of sourceFiles.filter((file) => /\.(ts|wxml)$/.test(file))) {
  const content = fs.readFileSync(filePath, "utf8");
  for (const match of content.matchAll(navigationPattern)) {
    const target = match[1];
    if (target.startsWith("pages/") && !pagePaths.includes(target)) {
      fail(`无效导航路径：${path.relative(projectDir, filePath)} -> ${target}`);
    }
  }
}

for (const pagePath of pagePaths) {
  const configPath = path.join(sourceDir, `${pagePath}.json`);
  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  for (const componentPath of Object.values(config.usingComponents || {})) {
    if (typeof componentPath !== "string" || componentPath.startsWith("plugin://")) continue;
    const resolved = componentPath.startsWith("/")
      ? path.join(sourceDir, componentPath)
      : path.resolve(path.dirname(configPath), componentPath);
    if (![".ts", ".js", ".json", ".wxml"].some((extension) => fs.existsSync(`${resolved}${extension}`))) {
      fail(`usingComponents 路径不存在：${pagePath} -> ${componentPath}`);
    }
  }
}

const allText = sourceFiles
  .filter((file) => /\.(ts|js|json|wxml|wxss)$/.test(file))
  .map((file) => fs.readFileSync(file, "utf8"))
  .join("\n");
const apiSource = read("miniprogram/services/api.ts");
const agentSource = read("miniprogram/pages/agent/agent.ts");
const agentViewSource = ["wxml", "wxss"]
  .map((extension) => read(`miniprogram/pages/agent/agent.${extension}`)).join("\n");
const homeSource = ["ts", "wxml", "wxss"]
  .map((extension) => read(`miniprogram/pages/index/index.${extension}`)).join("\n");

if (/\/logistics\/\$?\{/.test(allText)) fail("仍存在旧物流路径 /logistics/{orderId}");
for (const filePath of sourceFiles.filter((file) => file.endsWith(".ts"))) {
  if (filePath.endsWith(path.join("services", "api.ts"))) continue;
  if (/\bwx\.request\s*\(/.test(fs.readFileSync(filePath, "utf8"))) {
    fail(`业务页面直接调用 wx.request：${path.relative(projectDir, filePath)}`);
  }
}
if (!allText.includes("ResolveAI 智选商城")) fail("缺少统一品牌名称“ResolveAI 智选商城”");
if (!apiSource.includes("client_message_id")) fail("Agent 请求未携带 client_message_id");
if (!apiSource.includes("listSessions") || !apiSource.includes("getMessages")) fail("请求层缺少 Agent 会话历史接口");
if (!agentSource.includes("LAST_SESSION") || !agentSource.includes("getMessages")) fail("Agent 缺少最近会话恢复逻辑");
if (!agentSource.includes("pendingMemory") || !agentSource.includes("confirmMemory")) fail("Agent 缺少显式 Memory 确认逻辑");
if (!agentSource.includes("hasCitations")) fail("Agent citation 缺少稳定的展示标记");
if (/长期记忆/.test(agentViewSource)) fail("Agent 用户文案仍直接显示“长期记忆”");
if (!/page\s*\{[^}]*height\s*:\s*100%/s.test(agentViewSource)) fail("Agent 页面根节点未建立稳定高度");
if (!/\.message-bubble\s*\{[^}]*max-width\s*:\s*(?:7[6-9]|8[0-2])%/s.test(agentViewSource)) {
  fail("Agent 消息气泡最大宽度不在 76%～82% 范围");
}
if (!/\.message-input\s*\{[^}]*min-width\s*:\s*0/s.test(agentViewSource)) {
  fail("Agent 输入框缺少 min-width: 0");
}
if (/长期记忆|我的审批|pages\/(?:memories|approvals)\//.test(homeSource)) {
  fail("首页仍包含长期记忆或审批主入口");
}
if (!/\.category-grid\s*\{[^}]*grid-template-columns\s*:\s*repeat\(3,/s.test(homeSource)) {
  fail("首页商品分类未使用两行三列布局");
}
if (/\.category-grid\s*\{[^}]*grid-template-columns\s*:\s*repeat\(6,/s.test(homeSource)) {
  fail("首页商品分类仍使用六列紧凑布局");
}
if (!/\.product-name\s*\{[^}]*-webkit-line-clamp\s*:\s*2/s.test(homeSource)) {
  fail("首页商品名称未限制为最多两行");
}
if (!homeSource.includes("待上传商品图片")) fail("首页缺少明确的商品图片占位文案");
if (/writing-mode\s*:\s*vertical/.test(allText)) fail("页面仍使用竖排文字规避布局问题");

const cartFiles = ["ts", "json", "wxml", "wxss"].map(
  (extension) => path.join(sourceDir, `pages/cart/cart.${extension}`),
);
if (cartFiles.some((file) => !fs.existsSync(file))) {
  fail("购物车页面四件套缺失");
} else {
  const cartSource = [
    ...cartFiles.map((file) => fs.readFileSync(file, "utf8")),
    read("miniprogram/utils/cart.ts"),
  ].join("\n");
  if (!cartSource.includes("wx.getStorageSync") || !cartSource.includes("wx.setStorageSync")) {
    fail("购物车未使用本地账号隔离存储");
  }
  if (!cartSource.includes("当前演示版本暂未开放在线结算")) fail("购物车缺少结算边界说明");
  if (/\bwx\.request\s*\(|\/checkout|\/payment/.test(cartSource)) fail("购物车包含伪造结算或直接网络请求");
}

const productDetailSource = ["ts", "wxml"].map(
  (extension) => read(`miniprogram/pages/product-detail/product-detail.${extension}`),
).join("\n");
if (!productDetailSource.includes("addToCart")) fail("商品详情缺少加入购物车能力");
if (!productDetailSource.includes("wx.switchTab") || !productDetailSource.includes("pages/agent/agent")) {
  fail("商品详情缺少 AI 售后咨询入口");
}

for (const filePath of sourceFiles.filter((file) => /\.(wxml|wxss)$/.test(file))) {
  const content = fs.readFileSync(filePath, "utf8");
  if (/(?:src\s*=\s*["']https?:\/\/|url\(["']?https?:\/\/)/i.test(content)) {
    fail(`页面使用网络图片：${path.relative(projectDir, filePath)}`);
  }
}

const secretRules = [
  ["疑似硬编码 API Key", /(?:sk|dashscope)[-_][A-Za-z0-9]{16,}/],
  ["疑似 Authorization 凭据", /Authorization\s*[:=]\s*["'`]Bearer\s+(?!\$\{)[^"'`\s]+/i],
];
for (const [name, pattern] of secretRules) {
  if (pattern.test(allText)) fail(name);
}

if (failures.length > 0) {
  console.error(`小程序静态检查失败（${failures.length} 项）：`);
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`小程序静态检查通过：${pagePaths.length} 个页面，页面路径、请求层与安全规则均有效。`);
