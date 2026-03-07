// vite-env.d.ts

/// <reference types="vite/client" />

interface ImportMetaEnv {
  // You can explicitly declare your custom VITE_ variables here
  // For example, if you use VITE_API_BASE_URL:
  // readonly VITE_API_BASE_URL: string;

  // Vite's built-in variables are already included by the reference tag above, 
  // but you can add your own custom ones for better IntelliSense.
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}