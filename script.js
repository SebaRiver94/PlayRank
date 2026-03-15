/* script.js - PlayRank: Lógica de Transición */

const mockGroups = [
  {
    id: "1",
    name: "Los Mancos del Royale",
    game: "Fortnite",
    membersCount: 5,
    userRank: 2,
    icon: "🎮",
  },
  {
    id: "2",
    name: "Truco de los Viernes",
    game: "Truco",
    membersCount: 4,
    userRank: 1,
    icon: "🃏",
  },
  {
    id: "3",
    name: "FIFA Club",
    game: "FIFA 24",
    membersCount: 8,
    userRank: 3,
    icon: "⚽",
  },
];

function login(provider) {
  const loginScreen = document.getElementById("login-screen");
  const homeScreen = document.getElementById("home-screen");
  const authButtons = document.querySelectorAll(".auth-btn");

  // 1. Efecto visual en los botones
  console.log(`Iniciando sesión en PLAYRANK con ${provider}...`);
  authButtons.forEach((btn) => (btn.style.opacity = "0.5"));

  // 2. Transición de pantallas
  setTimeout(() => {
    loginScreen.style.display = "none";
    homeScreen.style.display = "flex";

    // 3. Cargar datos
    fetchGroups();
  }, 800);
}

async function fetchGroups() {
  const groupsContainer = document.getElementById("groups-container");
  if (!groupsContainer) return;

  groupsContainer.innerHTML =
    '<div style="color:white; text-align:center; margin-top:20px;">Cargando grupos de PLAYRANK...</div>';

  // Simulamos carga de API
  await new Promise((resolve) => setTimeout(resolve, 1000));
  groupsContainer.innerHTML = "";

  mockGroups.forEach((group) => {
    const cardHtml = `
            <div class="group-card">
                <div class="group-icon">${group.icon}</div>
                <div class="group-info">
                    <div class="group-name">${group.name}</div>
                    <div class="group-meta">
                        ${group.game} | ${group.membersCount} miembros | Rank: #${group.userRank}
                    </div>
                </div>
            </div>
        `;
    groupsContainer.innerHTML += cardHtml;
  });
}
