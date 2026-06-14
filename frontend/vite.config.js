import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    // Рекомендуемый способ для новых версий Vite на базе Rolldown
    rolldownOptions: {
      output: {
        manualChunks(id) {
          // Выносим 3D графику в отдельный чанк
          if (id.includes("node_modules/three") || id.includes("node_modules/@react-three")) {
            return "vendor-3d";
          }
          // Выносим эмодзи в отдельный чанк
          if (id.includes("node_modules/emoji-mart") || id.includes("node_modules/@emoji-mart")) {
            return "vendor-emoji";
          }
          // Остальные крупные библиотеки (React, Zustand и т.д.)
          if (id.includes("node_modules")) {
            return "vendor-core";
          }
        },
      },
    },
  },
});
