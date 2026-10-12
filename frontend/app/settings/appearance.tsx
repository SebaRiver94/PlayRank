import React from 'react';
import { View, Text, Alert, ScrollView } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';
import { ThemePicker } from '../../components/ThemePicker';
export default function Appearance() { const {theme,themeId,setTheme,busy}=useTheme(); return <ScrollView style={{flex:1,backgroundColor:theme.colors.background}} contentContainerStyle={{padding:24,paddingTop:60}}><Text style={{fontSize:26,fontWeight:'700',color:theme.colors.text,marginBottom:10}}>Apariencia</Text><Text style={{color:theme.colors.textMuted,marginBottom:24}}>Elegí cómo querés ver PlayRank. Tu preferencia se sincroniza con tu cuenta.</Text><ThemePicker value={themeId} disabled={busy} onChange={id=>{void setTheme(id).catch(()=>Alert.alert('No se pudo guardar','Comprobá tu conexión o volvé a intentarlo.'));}} /></ScrollView>; }
