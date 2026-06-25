// Injected at build time by Vite `define` (see vite.config.ts).
declare const __BUILD_INFO__: {
    /** App version from package.json */
    version: string;
    /** Short git SHA at build time (suffixed `-dirty` if the tree had uncommitted changes) */
    commit: string;
    /** ISO 8601 timestamp of when the frontend was built */
    buildTime: string;
};
