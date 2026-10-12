import { useTheme } from '../../theme/ThemeProvider';
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { useRouter, useFocusEffect } from 'expo-router';
import { ThemeColors } from '../../theme/themes';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Group { id: string; name: string; icon?: string; members: string[]; }

export default function MatchesScreen() {
  const { theme } = useTheme();
  const styles = React.useMemo(() => makeStyles(theme.colors), [theme]);
  const router = useRouter();
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(() => {
    axios.get(`${API_URL}/api/groups`)
      .then(r => setGroups(r.data)).catch(() => {})
      .finally(() => { setLoading(false); setRefreshing(false); });
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (loading) {
    return <View style={[styles.container, styles.center]}><ActivityIndicator size="large" color={theme.colors.primary} /></View>;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}><Text style={styles.title}>Partidas</Text></View>
      <FlatList
        data={groups}
        keyExtractor={g => g.id}
        contentContainerStyle={{ padding: 16 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={theme.colors.primary} />}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="trophy-outline" size={64} color={theme.colors.textMuted} />
            <Text style={styles.emptyText}>Sin partidas</Text>
            <Text style={styles.emptySubtext}>Unite o creá un grupo para registrar partidas.</Text>
          </View>
        }
        ListHeaderComponent={groups.length > 0 ? <Text style={styles.hint}>Elegí un grupo para ver y registrar partidas</Text> : null}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.card} onPress={() => router.push(`/group/${item.id}?section=partidas` as any)}>
            <View style={styles.cardIcon}><Text style={{ fontSize: 26 }}>{item.icon || '🎮'}</Text></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.cardTitle}>{item.name}</Text>
              <Text style={styles.cardSub}>{item.members.length} integrantes</Text>
            </View>
            <Ionicons name="chevron-forward" size={22} color={theme.colors.textMuted} />
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const makeStyles = (colors: ThemeColors) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  center: { alignItems: 'center', justifyContent: 'center' },
  header: { padding: 24, paddingTop: 16 },
  title: { fontSize: 28, fontWeight: 'bold', color: colors.text },
  hint: { color: colors.textMuted, fontSize: 13, marginBottom: 12 },
  card: { flexDirection: 'row', alignItems: 'center', gap: 14, backgroundColor: colors.surface, borderRadius: 14, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: colors.border },
  cardIcon: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  cardTitle: { color: colors.text, fontSize: 17, fontWeight: 'bold' },
  cardSub: { color: colors.textMuted, fontSize: 13, marginTop: 2 },
  emptyState: { alignItems: 'center', justifyContent: 'center', padding: 48, marginTop: 64 },
  emptyText: { fontSize: 20, fontWeight: 'bold', color: colors.text, marginTop: 16 },
  emptySubtext: { fontSize: 14, color: colors.textMuted, marginTop: 8, textAlign: 'center' },
});
