import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { THEME_IDS, ThemeId, themes } from '../theme/themes';
export function ThemePicker({ value, onChange, disabled = false }: { value: ThemeId; onChange: (id: ThemeId) => void; disabled?: boolean }) {
  return <View style={styles.list}>{THEME_IDS.map(id => {
    const t = themes[id]; const selected = value === id;
    return <TouchableOpacity key={id} accessibilityRole="radio" accessibilityState={{ checked: selected, disabled }} disabled={disabled} onPress={() => onChange(id)} style={[styles.card, { backgroundColor:t.colors.surface, borderColor: selected ? t.colors.primary : t.colors.border }]}>
      <View style={[styles.swatch, {backgroundColor:t.colors.background, borderColor:t.colors.primary}]}><View style={{width:17,height:17,borderRadius:9,backgroundColor:t.colors.accent}} /></View>
      <View style={{flex:1}}><Text style={{color:t.colors.text,fontWeight:'700',fontSize:16}}>{t.label} {selected ? '✓' : ''}</Text><Text style={{color:t.colors.textMuted}}>{t.description}</Text></View>
    </TouchableOpacity>;
  })}</View>;
}
const styles = StyleSheet.create({list:{gap:10},card:{flexDirection:'row',alignItems:'center',gap:12,padding:14,borderRadius:12,borderWidth:2},swatch:{height:40,width:40,borderRadius:10,borderWidth:2,alignItems:'center',justifyContent:'center'}});
