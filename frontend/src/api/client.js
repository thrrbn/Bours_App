import axios from "axios";

// Client HTTP unique vers l'API FastAPI - toute la logique d'appel API du
// frontend passe par ce module, jamais d'appel axios direct dans les
// composants (facilite le changement de base URL / l'ajout d'auth plus tard).
const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

export default apiClient;
