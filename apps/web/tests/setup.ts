import "@testing-library/jest-dom/vitest";

// Node 26 exposes localStorage as undefined; restore jsdom's implementation.
if (typeof window !== "undefined" && window.localStorage === undefined) {
  const storage: Record<string, string> = {};
  Object.defineProperty(window, "localStorage", {
    value: {
      getItem: (key: string) => storage[key] ?? null,
      setItem: (key: string, value: string) => {
        storage[key] = value;
      },
      removeItem: (key: string) => {
        delete storage[key];
      },
      clear: () => {
        Object.keys(storage).forEach((k) => delete storage[k]);
      },
      get length() {
        return Object.keys(storage).length;
      },
      key: (index: number) => Object.keys(storage)[index] ?? null,
    },
    writable: true,
  });
}
