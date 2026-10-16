import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// La clé Augure reste côté serveur : le navigateur appelle /api/augure,
// et le proxy de développement ajoute l'en-tête Authorization.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..", "");
  const base = env.AUGURE_BASE_URL || "https://api.augureai.ca/v1";

  return {
    plugins: [react()],
    define: {
      __AUGURE_MODEL__: JSON.stringify(env.AUGURE_MODEL || "rosedale-1"),
    },
    server: {
      proxy: {
        "/api/augure": {
          target: base,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/augure/, ""),
          headers: { Authorization: `Bearer ${env.AUGURE_API_KEY ?? ""}` },
        },
        // Backend Python (python -m backend.serveur).
        "/api/pipeline": "http://localhost:8000",
      },
    },
  };
});
