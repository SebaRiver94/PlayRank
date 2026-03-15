import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  Modal,
  Image,
} from 'react-native';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function ProfileScreen() {
  const { user, logout, updateUser } = useAuth();
  const [modalVisible, setModalVisible] = useState(false);
  const [externalModalVisible, setExternalModalVisible] = useState(false);
  const [username, setUsername] = useState(user?.username || '');
  const [bio, setBio] = useState(user?.bio || '');
  const [saving, setSaving] = useState(false);

  const [externalAccounts, setExternalAccounts] = useState({
    steam: user?.external_accounts?.steam || '',
    youtube: user?.external_accounts?.youtube || '',
    twitch: user?.external_accounts?.twitch || '',
    kick: user?.external_accounts?.kick || '',
  });

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Logout', style: 'destructive', onPress: () => logout() },
      ]
    );
  };

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.5,
      base64: true,
    });

    if (!result.canceled && result.assets[0].base64) {
      const base64Image = `data:image/jpeg;base64,${result.assets[0].base64}`;
      try {
        await axios.put(`${API_URL}/api/users/profile`, { avatar: base64Image });
        updateUser({ avatar: base64Image });
        Alert.alert('Success', 'Profile picture updated!');
      } catch (error) {
        Alert.alert('Error', 'Failed to update profile picture');
      }
    }
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await axios.put(`${API_URL}/api/users/profile`, {
        username,
        bio,
      });
      updateUser({ username, bio });
      setModalVisible(false);
      Alert.alert('Success', 'Profile updated!');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveExternalAccounts = async () => {
    setSaving(true);
    try {
      await axios.put(`${API_URL}/api/users/profile`, {
        external_accounts: externalAccounts,
      });
      updateUser({ external_accounts: externalAccounts });
      setExternalModalVisible(false);
      Alert.alert('Success', 'External accounts updated!');
    } catch (error) {
      Alert.alert('Error', 'Failed to update external accounts');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Profile</Text>
        <TouchableOpacity onPress={handleLogout}>
          <Ionicons name="log-out" size={24} color="#FF6B6B" />
        </TouchableOpacity>
      </View>

      <View style={styles.profileSection}>
        <TouchableOpacity style={styles.avatarContainer} onPress={pickImage}>
          {user?.avatar ? (
            <Image source={{ uri: user.avatar }} style={styles.avatar} />
          ) : (
            <View style={styles.avatarPlaceholder}>
              <Ionicons name="person" size={48} color="#666" />
            </View>
          )}
          <View style={styles.editBadge}>
            <Ionicons name="camera" size={16} color="#fff" />
          </View>
        </TouchableOpacity>

        <Text style={styles.username}>{user?.username}</Text>
        <Text style={styles.email}>{user?.email}</Text>
        {user?.bio && <Text style={styles.bio}>{user.bio}</Text>}

        <TouchableOpacity
          style={styles.editButton}
          onPress={() => setModalVisible(true)}
        >
          <Ionicons name="create" size={20} color="#00D9FF" />
          <Text style={styles.editButtonText}>Edit Profile</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Statistics</Text>
          <Ionicons name="stats-chart" size={20} color="#00D9FF" />
        </View>
        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>0</Text>
            <Text style={styles.statLabel}>Total Matches</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>0</Text>
            <Text style={styles.statLabel}>Wins</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>0%</Text>
            <Text style={styles.statLabel}>Win Rate</Text>
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Connected Accounts</Text>
          <TouchableOpacity onPress={() => setExternalModalVisible(true)}>
            <Ionicons name="add-circle" size={20} color="#00D9FF" />
          </TouchableOpacity>
        </View>

        {[
          { key: 'steam', icon: 'logo-steam', label: 'Steam' },
          { key: 'youtube', icon: 'logo-youtube', label: 'YouTube' },
          { key: 'twitch', icon: 'logo-twitch', label: 'Twitch' },
          { key: 'kick', icon: 'play', label: 'Kick' },
        ].map((account) => (
          <View key={account.key} style={styles.accountItem}>
            <View style={styles.accountLeft}>
              <Ionicons name={account.icon as any} size={24} color="#00D9FF" />
              <Text style={styles.accountLabel}>{account.label}</Text>
            </View>
            <Text style={styles.accountValue}>
              {user?.external_accounts?.[account.key] || 'Not connected'}
            </Text>
          </View>
        ))}
      </View>

      <Modal
        visible={modalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Edit Profile</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.input}
              placeholder="Username"
              placeholderTextColor="#666"
              value={username}
              onChangeText={setUsername}
            />

            <TextInput
              style={[styles.input, styles.textArea]}
              placeholder="Bio"
              placeholderTextColor="#666"
              value={bio}
              onChangeText={setBio}
              multiline
              numberOfLines={4}
            />

            <TouchableOpacity
              style={[styles.submitButton, saving && styles.submitButtonDisabled]}
              onPress={handleSaveProfile}
              disabled={saving}
            >
              <Text style={styles.submitButtonText}>
                {saving ? 'Saving...' : 'Save Changes'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      <Modal
        visible={externalModalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setExternalModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Connected Accounts</Text>
              <TouchableOpacity onPress={() => setExternalModalVisible(false)}>
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
            </View>

            <View style={styles.inputContainer}>
              <Ionicons name="logo-steam" size={20} color="#00D9FF" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Steam Profile URL"
                placeholderTextColor="#666"
                value={externalAccounts.steam}
                onChangeText={(text) => setExternalAccounts({ ...externalAccounts, steam: text })}
              />
            </View>

            <View style={styles.inputContainer}>
              <Ionicons name="logo-youtube" size={20} color="#00D9FF" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="YouTube Channel URL"
                placeholderTextColor="#666"
                value={externalAccounts.youtube}
                onChangeText={(text) => setExternalAccounts({ ...externalAccounts, youtube: text })}
              />
            </View>

            <View style={styles.inputContainer}>
              <Ionicons name="logo-twitch" size={20} color="#00D9FF" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Twitch Profile URL"
                placeholderTextColor="#666"
                value={externalAccounts.twitch}
                onChangeText={(text) => setExternalAccounts({ ...externalAccounts, twitch: text })}
              />
            </View>

            <View style={styles.inputContainer}>
              <Ionicons name="play" size={20} color="#00D9FF" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Kick Profile URL"
                placeholderTextColor="#666"
                value={externalAccounts.kick}
                onChangeText={(text) => setExternalAccounts({ ...externalAccounts, kick: text })}
              />
            </View>

            <TouchableOpacity
              style={[styles.submitButton, saving && styles.submitButtonDisabled]}
              onPress={handleSaveExternalAccounts}
              disabled={saving}
            >
              <Text style={styles.submitButtonText}>
                {saving ? 'Saving...' : 'Save Accounts'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
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
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  profileSection: {
    alignItems: 'center',
    padding: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  avatarContainer: {
    position: 'relative',
  },
  avatar: {
    width: 120,
    height: 120,
    borderRadius: 60,
  },
  avatarPlaceholder: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#1a1a1a',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#2a2a2a',
  },
  editBadge: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#00D9FF',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: '#0c0c0c',
  },
  username: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 16,
  },
  email: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  bio: {
    fontSize: 14,
    color: '#fff',
    marginTop: 12,
    textAlign: 'center',
  },
  editButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 24,
    marginTop: 16,
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  editButtonText: {
    color: '#00D9FF',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  section: {
    padding: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#00D9FF',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  accountItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  accountLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  accountLabel: {
    fontSize: 16,
    color: '#fff',
    marginLeft: 12,
    fontWeight: '600',
  },
  accountValue: {
    fontSize: 14,
    color: '#666',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    minHeight: 400,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0c0c0c',
    borderRadius: 12,
    paddingHorizontal: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    backgroundColor: '#0c0c0c',
    borderRadius: 12,
    padding: 16,
    color: '#fff',
    fontSize: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  submitButton: {
    backgroundColor: '#00D9FF',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  submitButtonDisabled: {
    opacity: 0.5,
  },
  submitButtonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
