import React, { useState, useEffect, useCallback } from 'react';
import { View, ScrollView, Alert, RefreshControl } from 'react-native';
import {
  Card,
  Text,
  Button,
  ActivityIndicator,
  ProgressBar,
  Divider,
  List,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../theme';
import api from '../services/api';
import {
  getAvailableProducts,
  purchaseTokens,
  isIAPAvailable,
  addPurchaseListener,
} from '../services/purchases';
import { TokenBalance } from '../types';

interface Props {
  navigation: any;
}

export default function PurchaseTokensScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const [balance, setBalance] = useState<TokenBalance | null>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [balanceData, productsData, txnData] = await Promise.all([
        api.getTokenBalance(),
        getAvailableProducts(),
        api.getTokenTransactions(10, 0),
      ]);
      setBalance(balanceData);
      setProducts(productsData);
      setTransactions(txnData.transactions || []);
    } catch (err) {
      console.error('Failed to load token data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const unsubscribe = addPurchaseListener((result) => {
      setPurchasing(null);
      if (result.success) {
        Alert.alert(
          'Purchase Successful!',
          `${formatTokens(result.tokensGranted || 0)} tokens have been added to your balance.`,
        );
        loadData(); // Refresh balance
      } else if (result.error) {
        Alert.alert('Purchase Failed', result.error);
      }
    });
    return unsubscribe;
  }, [loadData]);

  const handlePurchase = async (productId: string) => {
    if (!isIAPAvailable()) {
      Alert.alert(
        'Not Available',
        'In-app purchases require a production build. Token purchases are not available in development mode.',
      );
      return;
    }
    try {
      setPurchasing(productId);
      await purchaseTokens(productId);
    } catch (err: any) {
      setPurchasing(null);
      if (!err.message?.includes('cancelled')) {
        Alert.alert('Purchase Error', err.message || 'Could not start purchase');
      }
    }
  };

  const formatTokens = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
    return String(n);
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  const getResetDate = () => {
    if (!balance?.freeResetsAt) return 'N/A';
    const resetDate = new Date(balance.freeResetsAt);
    resetDate.setDate(resetDate.getDate() + 30);
    return resetDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  const freePercent = balance
    ? Math.min(balance.freeBalance / balance.freeMonthlyAllowance, 1)
    : 0;

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => { setRefreshing(true); loadData(); }}
        />
      }
    >
      {/* Current Balance */}
      <Card style={{ marginBottom: 16 }} mode="elevated">
        <Card.Content>
          <Text variant="titleMedium" style={{ marginBottom: 16 }}>Token Balance</Text>

          {/* Free tokens */}
          <View style={{ marginBottom: 16 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                Free Monthly Tokens
              </Text>
              <Text variant="labelMedium">
                {formatTokens(balance?.freeBalance || 0)} / {formatTokens(balance?.freeMonthlyAllowance || 100000)}
              </Text>
            </View>
            <ProgressBar
              progress={freePercent}
              style={{ borderRadius: 4, height: 8 }}
              color={freePercent < 0.1 ? theme.colors.error : theme.colors.primary}
            />
            <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}>
              Resets {getResetDate()}
            </Text>
          </View>

          {/* Purchased tokens */}
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <View>
              <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                Purchased Tokens
              </Text>
              <Text variant="titleLarge" style={{ fontWeight: '700' }}>
                {formatTokens(balance?.purchasedBalance || 0)}
              </Text>
            </View>
            <View style={{ alignItems: 'flex-end' }}>
              <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                Total Available
              </Text>
              <Text variant="titleLarge" style={{ fontWeight: '700', color: theme.colors.primary }}>
                {formatTokens(balance?.totalBalance || 0)}
              </Text>
            </View>
          </View>
        </Card.Content>
      </Card>

      {/* Purchase Tiers */}
      <Text variant="titleMedium" style={{ marginBottom: 12, paddingHorizontal: 4 }}>
        Buy Tokens
      </Text>

      {products.map((product) => {
        const isPurchasing = purchasing === product.productId;
        const isPopular = product.productId === 'pegasus_tokens_2m';

        return (
          <Card
            key={product.productId}
            style={{
              marginBottom: 12,
              borderWidth: isPopular ? 2 : 0,
              borderColor: isPopular ? theme.colors.primary : 'transparent',
            }}
            mode="elevated"
          >
            <Card.Content>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                <View style={{ flex: 1 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <Text variant="titleMedium" style={{ fontWeight: '700' }}>
                      {product.label}
                    </Text>
                    {isPopular && (
                      <View style={{
                        backgroundColor: theme.colors.primaryContainer,
                        paddingHorizontal: 8,
                        paddingVertical: 2,
                        borderRadius: 8,
                      }}>
                        <Text variant="labelSmall" style={{ color: theme.colors.primary }}>
                          Popular
                        </Text>
                      </View>
                    )}
                  </View>
                  <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginTop: 2 }}>
                    ${(product.priceUsd / (product.tokens / 1_000_000)).toFixed(2)}/M tokens
                  </Text>
                </View>
                <Button
                  mode="contained"
                  onPress={() => handlePurchase(product.productId)}
                  loading={isPurchasing}
                  disabled={purchasing !== null}
                  compact
                  style={{ minWidth: 80 }}
                >
                  {product.localizedPrice}
                </Button>
              </View>
            </Card.Content>
          </Card>
        );
      })}

      <Text
        variant="bodySmall"
        style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center', marginTop: 4, marginBottom: 20, paddingHorizontal: 16 }}
      >
        Purchased tokens never expire. Free tokens reset monthly.
        {'\n'}Each generation uses ~5K-50K tokens depending on lecture length.
      </Text>

      {/* Recent Transactions */}
      {transactions.length > 0 && (
        <>
          <Text variant="titleMedium" style={{ marginBottom: 8, paddingHorizontal: 4 }}>
            Recent Activity
          </Text>
          <Card mode="elevated">
            <Card.Content style={{ paddingVertical: 4 }}>
              {transactions.map((txn, idx) => {
                const isCredit = txn.tokenAmount > 0;
                return (
                  <React.Fragment key={txn.id}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8 }}>
                      <View style={{ flex: 1 }}>
                        <Text variant="bodySmall" numberOfLines={1}>
                          {txn.description || txn.transactionType}
                        </Text>
                        <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
                          {formatDate(txn.createdAt)}
                        </Text>
                      </View>
                      <Text
                        variant="bodyMedium"
                        style={{
                          fontWeight: '600',
                          color: isCredit ? '#4CAF50' : theme.colors.onSurfaceVariant,
                        }}
                      >
                        {isCredit ? '+' : ''}{formatTokens(txn.tokenAmount)}
                      </Text>
                    </View>
                    {idx < transactions.length - 1 && <Divider />}
                  </React.Fragment>
                );
              })}
            </Card.Content>
          </Card>
        </>
      )}
    </ScrollView>
  );
}
