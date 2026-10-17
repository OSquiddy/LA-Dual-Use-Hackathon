/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API?: "fixture" | "live";
  readonly VITE_BACKEND_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
