import { useTheme } from '../../theme/ThemeProvider';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  FlatList,
  TextInput,
  Modal,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Share,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { format } from 'date-fns';
import axios from 'axios';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '../../contexts/AuthContext';
import { ThemeColors } from '../../theme/themes';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

type Section = 'resumen' | 'clasificacion' | 'partidas' | 'chat';

interface Group { id: string; name: string; icon?: string; description?: string; owner_id: string; members: string[]; created_at: string; }
interface Member { id: string; username: string; avatar?: string; }
interface GameType { id: string; name: string; icon?: string; }
interface LeaderboardEntry { user_id: string; username: string; avatar?: string; total_matches: number; wins: number; losses: number; win_rate: number; current_streak: number; streak_type: string; }
interface MatchItem { id: string; game_type_id: string; date: string; players: string[]; winner_ids: string[]; score?: string; notes?: string; }
interface ChatMessage { id?: string; _id?: string; user_id: string; username: string; avatar?: string; content: string; created_at: string; }

export default function GroupDetailScreen() {
  const { theme } = useTheme();
  const styles = React.useMemo(() => makeStyles(theme.colors), [theme]);
  const { id, section } = useLocalSearchParams<{ id: string; section?: string }>();
  const router = useRouter();
  const { user, token } = useAuth();

  const [group, setGroup] = useState<Group | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [gameTypes, setGameTypes] = useState<GameType[]>([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState<Section>((section as Section) || 'resumen');

  const memberName = useCallback((uid: string) => members.find(m => m.id === uid)?.username || 'Jugador', [members]);

  const loadCore = useCallback(async () => {
    try {
      const [g, m, gt] = await Promise.all([
        axios.get(`${API_URL}/api/groups/${id}`),
        axios.get(`${API_URL}/api/groups/${id}/members`),
        axios.get(`${API_URL}/api/groups/${id}/game-types`),
      ]);
      setGroup(g.data);
      setMembers(m.data);
      setGameTypes(gt.data);
    } catch (e: any) {
      Alert.alert('Error', 'No se pudo cargar el grupo');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadCore(); }, [loadCore]);

  if (loading) {
    return <View style={[styles.container, styles.center]}><ActivityIndicator size="large" color={theme.colors.primary} /></View>;
  }

  const isOwner = group?.owner_id === user?.id;

  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={theme.colors.primary} />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={styles.groupTitle} numberOfLines={1}>{group?.icon || '🎮'} {group?.name}</Text>
          <Text style={styles.groupSub}>{group?.members.length} integrantes</Text>
        </View>
      </View>

      <View style={styles.tabsRow}>
        {([['resumen', 'Resumen'], ['clasificacion', 'Ranking'], ['partidas', 'Partidas'], ['chat', 'Chat']] as [Section, string][]).map(([key, label]) => (
          <TouchableOpacity key={key} style={[styles.tabBtn, active === key && styles.tabBtnActive]} onPress={() => setActive(key)}>
            <Text style={[styles.tabText, active === key && styles.tabTextActive]}>{label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {active === 'resumen' && (
        <OverviewSection group={group!} members={members} gameTypes={gameTypes} isOwner={isOwner}
          styles={styles} theme={theme} onReload={loadCore} />
      )}
      {active === 'clasificacion' && <LeaderboardSection groupId={id!} styles={styles} theme={theme} />}
      {active === 'partidas' && (
        <MatchesSection groupId={id!} members={members} gameTypes={gameTypes} memberName={memberName}
          styles={styles} theme={theme} />
      )}
      {active === 'chat' && (
        <ChatSection groupId={id!} token={token} currentUserId={user?.id} styles={styles} theme={theme} />
      )}
    </View>
  );
}

/* ---------------- Resumen ---------------- */
function OverviewSection({ group, members, gameTypes, isOwner, styles, theme, onReload }: any) {
  const [gtModal, setGtModal] = useState(false);
  const [gtName, setGtName] = useState('');
  const [gtIcon, setGtIcon] = useState('🎮');
  const [saving, setSaving] = useState(false);

  const shareCode = async () => {
    try { await Share.share({ message: `Unite a mi grupo "${group.name}" en PlayRank con este código:\n${group.id}` }); } catch {}
  };

  const createGameType = async () => {
    if (!gtName.trim()) { Alert.alert('Error', 'Ingresá un nombre de juego'); return; }
    setSaving(true);
    try {
      await axios.post(`${API_URL}/api/groups/${group.id}/game-types`, { name: gtName.trim(), icon: gtIcon });
      setGtModal(false); setGtName(''); setGtIcon('🎮');
      onReload();
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'No se pudo crear el juego');
    } finally { setSaving(false); }
  };

  return (
    <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 16 }}>
      {group.description ? <Text style={styles.description}>{group.description}</Text> : null}

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Código de invitación</Text>
        <Text style={styles.inviteCode} selectable>{group.id}</Text>
        <TouchableOpacity style={styles.inlineBtn} onPress={shareCode}>
          <Ionicons name="share-social" size={18} color={theme.colors.onPrimary} />
          <Text style={styles.inlineBtnText}>Compartir código</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.sectionHeaderRow}>
        <Text style={styles.sectionTitle}>Juegos ({gameTypes.length})</Text>
        <TouchableOpacity onPress={() => setGtModal(true)}>
          <Ionicons name="add-circle" size={24} color={theme.colors.primary} />
        </TouchableOpacity>
      </View>
      {gameTypes.length === 0 ? (
        <Text style={styles.muted}>Todavía no hay juegos. Creá uno para registrar partidas.</Text>
      ) : gameTypes.map((gt: GameType) => (
        <View key={gt.id} style={styles.rowItem}>
          <Text style={styles.rowIcon}>{gt.icon || '🎮'}</Text>
          <Text style={styles.rowText}>{gt.name}</Text>
        </View>
      ))}

      <View style={[styles.sectionHeaderRow, { marginTop: 24 }]}>
        <Text style={styles.sectionTitle}>Integrantes ({members.length})</Text>
      </View>
      {members.map((m: Member) => (
        <View key={m.id} style={styles.rowItem}>
          <Ionicons name="person-circle" size={28} color={theme.colors.primary} />
          <Text style={styles.rowText}>{m.username}{m.id === group.owner_id ? '  👑' : ''}</Text>
        </View>
      ))}

      <Modal visible={gtModal} transparent animationType="slide" onRequestClose={() => setGtModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Nuevo juego</Text>
              <TouchableOpacity onPress={() => setGtModal(false)}><Ionicons name="close" size={24} color={theme.colors.text} /></TouchableOpacity>
            </View>
            <View style={styles.emojiRow}>
              {['🎮', '♟️', '🃏', '🎯', '⚽', '🏓', '🎲', '🕹️'].map(e => (
                <TouchableOpacity key={e} onPress={() => setGtIcon(e)} style={[styles.emojiBtn, gtIcon === e && styles.emojiBtnActive]}>
                  <Text style={{ fontSize: 22 }}>{e}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <TextInput style={styles.input} placeholder="Nombre del juego" placeholderTextColor={theme.colors.textMuted} value={gtName} onChangeText={setGtName} />
            <TouchableOpacity style={[styles.submitButton, saving && styles.disabled]} onPress={createGameType} disabled={saving}>
              <Text style={styles.submitButtonText}>{saving ? 'Guardando...' : 'Crear juego'}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

/* ---------------- Clasificación ---------------- */
function LeaderboardSection({ groupId, styles, theme }: any) {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API_URL}/api/groups/${groupId}/leaderboard`)
      .then(r => setEntries(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [groupId]);

  if (loading) return <View style={styles.center}><ActivityIndicator color={theme.colors.primary} /></View>;
  if (entries.length === 0) return <EmptyState icon="podium-outline" title="Sin clasificación" subtitle="Registrá partidas para generar el ranking" styles={styles} theme={theme} />;

  return (
    <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 16 }}>
      {entries.map((e, i) => (
        <View key={e.user_id} style={styles.lbRow}>
          <Text style={[styles.lbRank, i === 0 && { color: theme.colors.gold }]}>{i + 1}</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.rowText}>{e.username}</Text>
            <Text style={styles.muted}>{e.wins}V · {e.losses}D · {e.win_rate.toFixed(0)}% victorias</Text>
          </View>
          <View style={styles.lbStat}>
            <Text style={styles.lbWins}>{e.wins}</Text>
            <Text style={styles.muted}>pts</Text>
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

/* ---------------- Partidas ---------------- */
function MatchesSection({ groupId, members, gameTypes, memberName, styles, theme }: any) {
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [gameTypeId, setGameTypeId] = useState('');
  const [selectedPlayers, setSelectedPlayers] = useState<string[]>([]);
  const [selectedWinners, setSelectedWinners] = useState<string[]>([]);
  const [score, setScore] = useState('');

  const load = useCallback(() => {
    axios.get(`${API_URL}/api/groups/${groupId}/matches`)
      .then(r => setMatches(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, [groupId]);
  useEffect(() => { load(); }, [load]);

  const togglePlayer = (uid: string) => setSelectedPlayers(p => p.includes(uid) ? p.filter(x => x !== uid) : [...p, uid]);
  const toggleWinner = (uid: string) => setSelectedWinners(w => w.includes(uid) ? w.filter(x => x !== uid) : [...w, uid]);

  const openModal = () => {
    if (gameTypes.length === 0) { Alert.alert('Falta un juego', 'Creá un juego en la pestaña Resumen antes de registrar una partida.'); return; }
    if (members.length < 2) { Alert.alert('Faltan jugadores', 'Necesitás al menos 2 integrantes en el grupo.'); return; }
    setGameTypeId(gameTypes[0].id); setSelectedPlayers([]); setSelectedWinners([]); setScore('');
    setModal(true);
  };

  const submit = async () => {
    if (!gameTypeId) { Alert.alert('Error', 'Elegí un juego'); return; }
    if (selectedPlayers.length < 2) { Alert.alert('Error', 'Elegí al menos 2 jugadores'); return; }
    const winners = selectedWinners.filter(w => selectedPlayers.includes(w));
    if (winners.length === 0) { Alert.alert('Error', 'Elegí al menos un ganador'); return; }
    setSaving(true);
    try {
      await axios.post(`${API_URL}/api/matches`, {
        game_type_id: gameTypeId, group_id: groupId, date: new Date().toISOString(),
        players: selectedPlayers, winner_ids: winners, score: score.trim() || null,
      });
      setModal(false); load();
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'No se pudo registrar la partida');
    } finally { setSaving(false); }
  };

  const gtName = (gid: string) => gameTypes.find((g: GameType) => g.id === gid)?.name || 'Partida';

  return (
    <View style={{ flex: 1 }}>
      <TouchableOpacity style={styles.fab} onPress={openModal}>
        <Ionicons name="add" size={28} color={theme.colors.onPrimary} />
      </TouchableOpacity>

      {loading ? <View style={styles.center}><ActivityIndicator color={theme.colors.primary} /></View>
        : matches.length === 0 ? <EmptyState icon="trophy-outline" title="Sin partidas" subtitle="Tocá + para registrar la primera" styles={styles} theme={theme} />
          : (
            <FlatList data={matches} keyExtractor={m => m.id} contentContainerStyle={{ padding: 16 }}
              renderItem={({ item }) => (
                <View style={styles.matchCard}>
                  <View style={styles.matchHeader}>
                    <Text style={styles.matchGame}>{gtName(item.game_type_id)}</Text>
                    <Text style={styles.muted}>{format(new Date(item.date), 'd MMM, HH:mm')}</Text>
                  </View>
                  <Text style={styles.muted}>Jugadores: {item.players.map(memberName).join(', ')}</Text>
                  <Text style={styles.matchWinner}>🏆 {item.winner_ids.map(memberName).join(', ')}</Text>
                  {item.score ? <Text style={styles.muted}>Resultado: {item.score}</Text> : null}
                </View>
              )} />
          )}

      <Modal visible={modal} transparent animationType="slide" onRequestClose={() => setModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { maxHeight: '85%' }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Registrar partida</Text>
              <TouchableOpacity onPress={() => setModal(false)}><Ionicons name="close" size={24} color={theme.colors.text} /></TouchableOpacity>
            </View>
            <ScrollView>
              <Text style={styles.cardLabel}>Juego</Text>
              <View style={styles.chipRow}>
                {gameTypes.map((gt: GameType) => (
                  <TouchableOpacity key={gt.id} onPress={() => setGameTypeId(gt.id)} style={[styles.chip, gameTypeId === gt.id && styles.chipActive]}>
                    <Text style={[styles.chipText, gameTypeId === gt.id && styles.chipTextActive]}>{gt.icon || '🎮'} {gt.name}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.cardLabel}>Jugadores</Text>
              {members.map((m: Member) => (
                <TouchableOpacity key={m.id} style={styles.selectRow} onPress={() => togglePlayer(m.id)}>
                  <Ionicons name={selectedPlayers.includes(m.id) ? 'checkbox' : 'square-outline'} size={22} color={theme.colors.primary} />
                  <Text style={styles.rowText}>{m.username}</Text>
                </TouchableOpacity>
              ))}

              {selectedPlayers.length > 0 && (
                <>
                  <Text style={styles.cardLabel}>Ganadores</Text>
                  {members.filter((m: Member) => selectedPlayers.includes(m.id)).map((m: Member) => (
                    <TouchableOpacity key={m.id} style={styles.selectRow} onPress={() => toggleWinner(m.id)}>
                      <Ionicons name={selectedWinners.includes(m.id) ? 'checkbox' : 'square-outline'} size={22} color={theme.colors.gold} />
                      <Text style={styles.rowText}>{m.username}</Text>
                    </TouchableOpacity>
                  ))}
                </>
              )}

              <Text style={styles.cardLabel}>Resultado (opcional)</Text>
              <TextInput style={styles.input} placeholder="ej. 3-1" placeholderTextColor={theme.colors.textMuted} value={score} onChangeText={setScore} />

              <TouchableOpacity style={[styles.submitButton, saving && styles.disabled]} onPress={submit} disabled={saving}>
                <Text style={styles.submitButtonText}>{saving ? 'Guardando...' : 'Registrar partida'}</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

/* ---------------- Chat ---------------- */
function ChatSection({ groupId, token, currentUserId, styles, theme }: any) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState('');
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);
  const listRef = useRef<FlatList>(null);

  useEffect(() => {
    axios.get(`${API_URL}/api/groups/${groupId}/messages`).then(r => setMessages(r.data)).catch(() => {});

    const socket = io(API_URL as string, { path: '/api/socket.io', transports: ['polling', 'websocket'], auth: { token } });
    socketRef.current = socket;
    socket.on('connect', () => { setConnected(true); socket.emit('join_group', { group_id: groupId }); });
    socket.on('disconnect', () => setConnected(false));
    socket.on('new_message', (msg: ChatMessage) => setMessages(prev => [...prev, msg]));
    return () => { socket.emit('leave_group', { group_id: groupId }); socket.disconnect(); };
  }, [groupId, token]);

  const send = () => {
    const content = text.trim();
    if (!content || !socketRef.current) return;
    socketRef.current.emit('send_message', { group_id: groupId, content });
    setText('');
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(m, i) => m.id || m._id || String(i)}
        contentContainerStyle={{ padding: 16 }}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        ListEmptyComponent={<EmptyState icon="chatbubbles-outline" title="Sin mensajes" subtitle="Escribí el primero" styles={styles} theme={theme} />}
        renderItem={({ item }) => {
          const mine = item.user_id === currentUserId;
          return (
            <View style={[styles.msgRow, mine ? styles.msgMine : styles.msgOther]}>
              {!mine && <Text style={styles.msgUser}>{item.username}</Text>}
              <Text style={[styles.msgText, mine && { color: theme.colors.onPrimary }]}>{item.content}</Text>
            </View>
          );
        }}
      />
      <View style={styles.chatInputBar}>
        <TextInput style={styles.chatInput} placeholder={connected ? 'Mensaje...' : 'Conectando...'} placeholderTextColor={theme.colors.textMuted} value={text} onChangeText={setText} onSubmitEditing={send} returnKeyType="send" />
        <TouchableOpacity style={styles.sendBtn} onPress={send}>
          <Ionicons name="send" size={20} color={theme.colors.onPrimary} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

function EmptyState({ icon, title, subtitle, styles, theme }: any) {
  return (
    <View style={styles.emptyState}>
      <Ionicons name={icon} size={56} color={theme.colors.textMuted} />
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.muted}>{subtitle}</Text>
    </View>
  );
}

const makeStyles = (colors: ThemeColors) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  topBar: { flexDirection: 'row', alignItems: 'center', paddingTop: 50, paddingHorizontal: 16, paddingBottom: 12, gap: 8 },
  backButton: { padding: 4 },
  groupTitle: { color: colors.text, fontSize: 20, fontWeight: 'bold' },
  groupSub: { color: colors.textMuted, fontSize: 13 },
  tabsRow: { flexDirection: 'row', paddingHorizontal: 12, gap: 6, marginBottom: 8 },
  tabBtn: { flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center', backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  tabBtnActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  tabText: { color: colors.textMuted, fontWeight: '600', fontSize: 13 },
  tabTextActive: { color: colors.onPrimary },
  description: { color: colors.text, fontSize: 15, marginBottom: 16, lineHeight: 21 },
  card: { backgroundColor: colors.surface, borderRadius: 14, padding: 16, borderWidth: 1, borderColor: colors.border, marginBottom: 20 },
  cardLabel: { color: colors.textMuted, fontSize: 13, marginBottom: 6, marginTop: 8 },
  inviteCode: { color: colors.primary, fontSize: 15, fontWeight: '700', marginBottom: 12 },
  inlineBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: colors.primary, borderRadius: 10, paddingVertical: 10 },
  inlineBtnText: { color: colors.onPrimary, fontWeight: '700' },
  sectionHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  sectionTitle: { color: colors.text, fontSize: 18, fontWeight: 'bold' },
  muted: { color: colors.textMuted, fontSize: 13 },
  rowItem: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: colors.surface, borderRadius: 10, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: colors.border },
  rowIcon: { fontSize: 22 },
  rowText: { color: colors.text, fontSize: 15, fontWeight: '600' },
  lbRow: { flexDirection: 'row', alignItems: 'center', gap: 14, backgroundColor: colors.surface, borderRadius: 12, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: colors.border },
  lbRank: { color: colors.text, fontSize: 20, fontWeight: 'bold', width: 28, textAlign: 'center' },
  lbStat: { alignItems: 'center' },
  lbWins: { color: colors.primary, fontSize: 20, fontWeight: 'bold' },
  matchCard: { backgroundColor: colors.surface, borderRadius: 12, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: colors.border, gap: 4 },
  matchHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 },
  matchGame: { color: colors.text, fontSize: 16, fontWeight: 'bold' },
  matchWinner: { color: colors.gold, fontSize: 14, fontWeight: '600' },
  emptyState: { alignItems: 'center', justifyContent: 'center', padding: 48, marginTop: 48 },
  emptyTitle: { color: colors.text, fontSize: 18, fontWeight: 'bold', marginTop: 14 },
  fab: { position: 'absolute', right: 20, bottom: 20, zIndex: 10, width: 56, height: 56, borderRadius: 28, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center', elevation: 4 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, minHeight: 300 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  modalTitle: { color: colors.text, fontSize: 22, fontWeight: 'bold' },
  input: { backgroundColor: colors.background, borderRadius: 10, padding: 14, color: colors.text, fontSize: 16, marginBottom: 14, borderWidth: 1, borderColor: colors.border },
  submitButton: { backgroundColor: colors.primary, borderRadius: 12, padding: 16, alignItems: 'center', marginTop: 8, marginBottom: 20 },
  submitButtonText: { color: colors.onPrimary, fontSize: 16, fontWeight: 'bold' },
  disabled: { opacity: 0.5 },
  emojiRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 14 },
  emojiBtn: { width: 44, height: 44, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border },
  emojiBtnActive: { borderColor: colors.primary, borderWidth: 2 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  chip: { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { color: colors.text, fontWeight: '600' },
  chipTextActive: { color: colors.onPrimary },
  selectRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 8 },
  msgRow: { maxWidth: '80%', padding: 10, borderRadius: 14, marginBottom: 8 },
  msgMine: { alignSelf: 'flex-end', backgroundColor: colors.primary },
  msgOther: { alignSelf: 'flex-start', backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  msgUser: { color: colors.accent, fontSize: 12, fontWeight: '700', marginBottom: 2 },
  msgText: { color: colors.text, fontSize: 15 },
  chatInputBar: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.surface },
  chatInput: { flex: 1, backgroundColor: colors.background, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, color: colors.text, fontSize: 15, borderWidth: 1, borderColor: colors.border },
  sendBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
});
