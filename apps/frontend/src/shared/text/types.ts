type Join<K extends string, P extends string> = `${K}.${P}`;

export type NestedLeafKey<T> = T extends string | number | boolean | null | undefined
  ? never
  : {
      [K in keyof T & string]: T[K] extends string | number | boolean | null | undefined
        ? K
        : Join<K, NestedLeafKey<T[K]>>;
    }[keyof T & string];
