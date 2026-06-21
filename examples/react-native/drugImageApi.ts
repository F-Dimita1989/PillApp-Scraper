/**
 * Client API — punta al backend C# su Render (che fa proxy verso Python).
 *
 * .env Expo:
 *   EXPO_PUBLIC_API_URL=https://pillapp-api.onrender.com
 *
 * Il C# espone POST /api/v1/drugs/image (camelCase nel body RN).
 */

import type { DrugInfoPayload, ImageFetchResponse } from './types';

const API_BASE =
  process.env.EXPO_PUBLIC_DRUG_IMAGE_API_URL ??
  process.env.EXPO_PUBLIC_API_URL ?? // stesso backend Render PillApp
  'http://localhost:8000';

const DEFAULT_TIMEOUT_MS = 25_000;

export class DrugImageApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
  ) {
    super(message);
    this.name = 'DrugImageApiError';
  }
}

export async function fetchDrugPackageImage(
  drug: DrugInfoPayload,
  options?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<ImageFetchResponse> {
  const controller = new AbortController();
  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  // Se il chiamante passa un signal esterno, abort anche su quello
  const onExternalAbort = () => controller.abort();
  options?.signal?.addEventListener('abort', onExternalAbort);

  try {
    const response = await fetch(`${API_BASE}/api/v1/drugs/image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        aic: drug.aic,
        name: drug.name,
        dosage: drug.dosage ?? null,
        // C# accetta camelCase; inoltra snake_case al Python internamente
        pharmaceuticalForm: drug.pharmaceutical_form ?? null,
        packageQuantity: drug.package_quantity ?? null,
        marketingAuthorizationHolder: drug.marketing_authorization_holder ?? null,
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new DrugImageApiError(
        `Errore server (${response.status})`,
        response.status,
      );
    }

    return (await response.json()) as ImageFetchResponse;
  } catch (error) {
    if (error instanceof DrugImageApiError) throw error;
    if (error instanceof Error && error.name === 'AbortError') {
      throw new DrugImageApiError('Timeout recupero immagine');
    }
    throw new DrugImageApiError('Rete non disponibile');
  } finally {
    clearTimeout(timeout);
    options?.signal?.removeEventListener('abort', onExternalAbort);
  }
}

export async function checkDrugImageServiceHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) return false;
    const data = (await response.json()) as { status?: string };
    return data.status === 'ok';
  } catch {
    return false;
  }
}
