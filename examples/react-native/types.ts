/**
 * Tipi per l'integrazione con il backend drug image.
 * Copia in: src/types/drugImage.ts
 */

export interface DrugImageRequest {
  aic: string;
  name?: string | null;
}

export interface DrugImageResponse {
  success: boolean;
  imageUrl: string | null;
  sourcePageUrl: string | null;
  message: string;
}

export type DrugImageState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: DrugImageResponse }
  | { status: 'unavailable'; data: DrugImageResponse }
  | { status: 'error'; error: string };
