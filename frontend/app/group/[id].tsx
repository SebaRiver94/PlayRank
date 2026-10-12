
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function GroupDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.backButton}
        onPress={() => router.back()}
      >
        <Ionicons name="arrow-back" size={24} color="#00D9FF" />
        <Text style={styles.backText}>Volver a grupos</Text>
      </TouchableOpacity>

      <View style={styles.content}>
        <Ionicons name="people" size={64} color="#00D9FF" />

        <Text style={styles.title}>Detalle del grupo</Text>

        <Text style={styles.subtitle}>
          La navegación del grupo está funcionando.
        </Text>

        <Text style={styles.groupId}>
          ID: {id || 'No disponible'}
        </Text>

        <Text style={styles.message}>
          Próximamente: integrantes, partidas, rankings y chat.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
    padding: 24,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 32,
    gap: 8,
  },
  backText: {
    color: '#00D9FF',
    fontSize: 16,
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    color: '#fff',
    fontSize: 26,
    fontWeight: 'bold',
    marginTop: 20,
  },
  subtitle: {
    color: '#aaa',
    fontSize: 16,
    marginTop: 12,
    textAlign: 'center',
  },
  groupId: {
    color: '#00D9FF',
    fontSize: 12,
    marginTop: 16,
  },
  message: {
    color: '#888',
    fontSize: 14,
    marginTop: 32,
    textAlign: 'center',
  },
});
