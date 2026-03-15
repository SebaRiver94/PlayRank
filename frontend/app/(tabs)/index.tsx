import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { format } from 'date-fns';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Group {
  id: string;
  name: string;
  icon?: string;
  members: string[];
}

interface Activity {
  id: string;
  username: string;
  description: string;
  created_at: string;
}

export default function HomeScreen() {
  const { user } = useAuth();
  const [groups, setGroups] = useState<Group[]>([]);
  const [recentActivities, setRecentActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const groupsRes = await axios.get(`${API_URL}/api/groups`);
      setGroups(groupsRes.data);

      // Load recent activities from all groups
      const activities: Activity[] = [];
      for (const group of groupsRes.data.slice(0, 3)) {
        try {
          const actRes = await axios.get(`${API_URL}/api/groups/${group.id}/activities?limit=5`);
          activities.push(...actRes.data);
        } catch (error) {
          console.error('Error loading activities:', error);
        }
      }
      
      // Sort by date and take top 10
      activities.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setRecentActivities(activities.slice(0, 10));
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#00D9FF" />}
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Welcome back,</Text>
          <Text style={styles.username}>{user?.username}</Text>
        </View>
        <Ionicons name="game-controller" size={32} color="#00D9FF" />
      </View>

      <View style={styles.statsGrid}>
        <View style={styles.statCard}>
          <Ionicons name="people" size={24} color="#00D9FF" />
          <Text style={styles.statValue}>{groups.length}</Text>
          <Text style={styles.statLabel}>Groups</Text>
        </View>
        <View style={styles.statCard}>
          <Ionicons name="trophy" size={24} color="#FFD700" />
          <Text style={styles.statValue}>0</Text>
          <Text style={styles.statLabel}>Wins</Text>
        </View>
        <View style={styles.statCard}>
          <Ionicons name="flame" size={24} color="#FF6B6B" />
          <Text style={styles.statValue}>0</Text>
          <Text style={styles.statLabel}>Streak</Text>
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Recent Activity</Text>
          <Ionicons name="time" size={20} color="#00D9FF" />
        </View>

        {recentActivities.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="newspaper-outline" size={48} color="#666" />
            <Text style={styles.emptyText}>No recent activity</Text>
            <Text style={styles.emptySubtext}>Join a group and start competing!</Text>
          </View>
        ) : (
          recentActivities.map((activity) => (
            <View key={activity.id} style={styles.activityCard}>
              <View style={styles.activityIcon}>
                <Ionicons name="notifications" size={20} color="#00D9FF" />
              </View>
              <View style={styles.activityContent}>
                <Text style={styles.activityText}>{activity.description}</Text>
                <Text style={styles.activityTime}>
                  {format(new Date(activity.created_at), 'MMM d, h:mm a')}
                </Text>
              </View>
            </View>
          ))
        )}
      </View>

      {groups.length === 0 && (
        <View style={styles.section}>
          <View style={styles.welcomeCard}>
            <Ionicons name="rocket" size={48} color="#00D9FF" />
            <Text style={styles.welcomeTitle}>Get Started!</Text>
            <Text style={styles.welcomeText}>
              Create or join a group to start tracking your competitions with friends
            </Text>
          </View>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 24,
    paddingTop: 16,
  },
  greeting: {
    fontSize: 16,
    color: '#666',
  },
  username: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 4,
  },
  statsGrid: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  section: {
    padding: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  activityCard: {
    flexDirection: 'row',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  activityIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(0, 217, 255, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  activityContent: {
    flex: 1,
  },
  activityText: {
    fontSize: 14,
    color: '#fff',
    marginBottom: 4,
  },
  activityTime: {
    fontSize: 12,
    color: '#666',
  },
  emptyState: {
    alignItems: 'center',
    padding: 32,
  },
  emptyText: {
    fontSize: 18,
    color: '#fff',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
  },
  welcomeCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 32,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  welcomeTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 16,
  },
  welcomeText: {
    fontSize: 16,
    color: '#666',
    marginTop: 12,
    textAlign: 'center',
  },
  loadingText: {
    color: '#fff',
    fontSize: 16,
  },
});
