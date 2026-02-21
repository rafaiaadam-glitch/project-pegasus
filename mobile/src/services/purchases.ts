/**
 * In-App Purchase service wrapping react-native-iap.
 *
 * Handles:
 * - Store connection/disconnection
 * - Product fetching
 * - Purchase flow
 * - Receipt verification with backend
 */

import { Platform } from 'react-native';
import api from './api';

// Product IDs must match App Store Connect / Google Play Console
const PRODUCT_IDS = [
  'pegasus_tokens_500k',
  'pegasus_tokens_2m',
  'pegasus_tokens_5m',
];

type PurchaseListener = (result: { success: boolean; tokensGranted?: number; error?: string }) => void;

let purchaseListeners: PurchaseListener[] = [];
let iapModule: any = null;
let purchaseSubscription: any = null;
let errorSubscription: any = null;

/**
 * Initialize the IAP service. Call once after auth check.
 * Silently fails if react-native-iap is not installed (dev builds without native modules).
 */
export async function initializePurchases(): Promise<void> {
  try {
    iapModule = require('react-native-iap');
    await iapModule.initConnection();

    // Listen for completed purchases
    purchaseSubscription = iapModule.purchaseUpdatedListener(
      async (purchase: any) => {
        try {
          const receipt = purchase.transactionReceipt || purchase.purchaseToken;
          if (!receipt) return;

          let result: any;
          if (Platform.OS === 'ios') {
            result = await api.verifyApplePurchase(
              purchase.transactionId,
              receipt,
            );
          } else {
            result = await api.verifyGooglePurchase(
              receipt,
              purchase.productId,
            );
          }

          // Acknowledge the purchase (required by both stores)
          if (Platform.OS === 'ios') {
            await iapModule.finishTransaction({ purchase, isConsumable: true });
          } else {
            await iapModule.acknowledgePurchaseAndroid({ token: purchase.purchaseToken });
            await iapModule.finishTransaction({ purchase, isConsumable: true });
          }

          notifyListeners({
            success: true,
            tokensGranted: result.tokensGranted,
          });
        } catch (err: any) {
          notifyListeners({
            success: false,
            error: err.message || 'Purchase verification failed',
          });
        }
      },
    );

    // Listen for purchase errors
    errorSubscription = iapModule.purchaseErrorListener((error: any) => {
      // User cancelled is not a real error
      if (error.code === 'E_USER_CANCELLED') return;
      notifyListeners({
        success: false,
        error: error.message || 'Purchase failed',
      });
    });
  } catch {
    // react-native-iap not available (Expo Go, web, etc.)
    console.log('[IAP] react-native-iap not available — purchases disabled');
    iapModule = null;
  }
}

/**
 * Get available products from the native store.
 * Falls back to backend product catalog if native store is unavailable.
 */
export async function getAvailableProducts(): Promise<any[]> {
  // Always fetch backend catalog for token counts
  const backendProducts = await api.getProducts();
  const catalog = backendProducts.products;

  if (!iapModule) {
    // Return backend catalog with placeholder prices
    return catalog.map((p: any) => ({
      ...p,
      localizedPrice: `$${p.priceUsd.toFixed(2)}`,
      nativeProduct: null,
    }));
  }

  try {
    const nativeProducts = await iapModule.getProducts({ skus: PRODUCT_IDS });
    // Merge native pricing with backend token info
    return catalog.map((p: any) => {
      const native = nativeProducts.find((np: any) => np.productId === p.productId);
      return {
        ...p,
        localizedPrice: native?.localizedPrice || `$${p.priceUsd.toFixed(2)}`,
        nativeProduct: native || null,
      };
    });
  } catch {
    return catalog.map((p: any) => ({
      ...p,
      localizedPrice: `$${p.priceUsd.toFixed(2)}`,
      nativeProduct: null,
    }));
  }
}

/**
 * Initiate a purchase flow for a product.
 */
export async function purchaseTokens(productId: string): Promise<void> {
  if (!iapModule) {
    throw new Error('In-app purchases are not available on this device.');
  }
  await iapModule.requestPurchase({ sku: productId });
}

/**
 * Check if IAP is available.
 */
export function isIAPAvailable(): boolean {
  return iapModule !== null;
}

/**
 * Register a listener for purchase results.
 */
export function addPurchaseListener(listener: PurchaseListener): () => void {
  purchaseListeners.push(listener);
  return () => {
    purchaseListeners = purchaseListeners.filter((l) => l !== listener);
  };
}

function notifyListeners(result: { success: boolean; tokensGranted?: number; error?: string }) {
  purchaseListeners.forEach((l) => l(result));
}

/**
 * Clean up IAP connections. Call on app unmount.
 */
export async function destroyPurchases(): Promise<void> {
  if (purchaseSubscription) {
    purchaseSubscription.remove();
    purchaseSubscription = null;
  }
  if (errorSubscription) {
    errorSubscription.remove();
    errorSubscription = null;
  }
  if (iapModule) {
    try {
      await iapModule.endConnection();
    } catch {
      // ignore
    }
  }
  purchaseListeners = [];
}
