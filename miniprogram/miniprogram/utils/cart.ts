const CART_PREFIX = "resolveai_cart_v1";

function currentCartKey(): string {
  const user = getApp<IAppOption>().globalData.userInfo;
  return `${CART_PREFIX}:${user?.id || user?.email || "anonymous"}`;
}

export function loadCart(): CartItem[] {
  const value = wx.getStorageSync(currentCartKey()) as CartItem[];
  return Array.isArray(value) ? value : [];
}

export function saveCart(items: CartItem[]): void {
  wx.setStorageSync(currentCartKey(), items);
}

export function addProductToCart(product: Product): void {
  const items = loadCart();
  const existing = items.find((item) => item.product.id === product.id);
  if (existing) existing.quantity += 1;
  else items.push({ product, quantity: 1, selected: true });
  saveCart(items);
}
