import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '../../theme/ThemeProvider';
export default function Settings() { const router = useRouter(); const {theme}=useTheme(); return <View style={{flex:1,backgroundColor:theme.colors.background,padding:24,paddingTop:60}}><Text style={{fontSize:26,fontWeight:'700',color:theme.colors.text,marginBottom:25}}>Configuración</Text><TouchableOpacity onPress={()=>router.push('/settings/appearance')} style={{backgroundColor:theme.colors.surface,padding:18,borderRadius:12,borderColor:theme.colors.border,borderWidth:1}}><Text style={{color:theme.colors.text,fontSize:17}}>🎨 Apariencia  →</Text></TouchableOpacity></View>; }
