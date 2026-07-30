import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";

const fromProjectRoot = (path: string) =>
  fileURLToPath(new URL(path, import.meta.url));

export default defineConfig({
  root: fromProjectRoot("./netlify/"),
  publicDir: fromProjectRoot("./public/"),
  plugins: [react()],
  build: {
    outDir: fromProjectRoot("./dist/netlify/"),
    emptyOutDir: true,
    sourcemap: true,
  },
});
