import { useEffect, useState } from "react";

/** useState that survives a page reload (localStorage). Falls back to `initial` on bad data. */
export function useStored<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(`dnb.${key}`);
      return raw === null ? initial : (JSON.parse(raw) as T);
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    localStorage.setItem(`dnb.${key}`, JSON.stringify(value));
  }, [key, value]);
  return [value, setValue] as const;
}
