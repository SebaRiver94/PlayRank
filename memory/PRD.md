# PlayRank — PRD / Estado

App social de ranking para videojuegos, juegos de cartas y de mesa.
Stack: Expo (React Native, expo-router) · FastAPI · MongoDB · Socket.IO.
Idioma del usuario: **Español**.

## Implementado y probado
- **Temas Neo / Sakura / Core**: aplicados en todas las pantallas, con persistencia por cuenta (versionado con compare-and-set en backend). Selección en registro y en Configuración → Apariencia.
- **Auth**: registro, login, persistencia de sesión, logout, edición de perfil.
- **Hub de grupo** (`app/group/[id].tsx`): Resumen (código de invitación compartible, juegos, integrantes), Ranking (leaderboard real), Partidas (lista + registrar partida con jugadores/ganadores/resultado), Chat en tiempo real (Socket.IO por transporte polling).
- **Unirse a grupo por código** (ID del grupo) desde la pestaña Grupos.
- **Estadísticas reales** agregadas en Home (victorias, mejor racha) y Perfil (partidas, victorias, % victorias).
- **Tab bar** con colores del tema.

## Backend
- Modular: routers (auth, users, groups, game_types, matches, rankings, social), models, services, core, realtime/socket.
- Tests: 87 passed (pytest).

## Integraciones externas (identificadas, requieren credenciales del usuario)
- Google / Discord social login, Steam / PlayStation / Xbox / Epic: requieren credenciales OAuth/API oficiales. No se simulan. Hoy los perfiles externos se guardan como enlaces manuales en el perfil.

## Notas técnicas
- El transporte WebSocket de Socket.IO devuelve 403 en el ingress; el cliente usa `transports: ['polling','websocket']` (conecta por polling).
- Credenciales de prueba en `/app/memory/test_credentials.md`.
- Rama de desarrollo: `feature/themes-neo-sakura-core`. Respaldo intacto: `playrank-backup-12102026`.
