/**
 * Tipi condivisi con il backend FastAPI (examples/fastapi_integration.py).
 * Copia in: src/types/drugImage.ts
 */

export interface DrugInfoPayload {
  aic: string;
  name: string;
  dosage?: string | null;
  pharmaceutical_form?: string | null;
  package_quantity?: string | null;
  marketing_authorization_holder?: string | null;
}

export interface ImageFetchResponse {
  success: boolean;
  imageUrl: string | null;
  sourcePageUrl: string | null;
  confidenceScore: number;
  matchedFields: string[];
  rejectedReasons: string[];
  message: string;
}

export type DrugImageState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: ImageFetchResponse }
  | { status: 'unavailable'; data: ImageFetchResponse }
  | { status: 'error'; error: string };
