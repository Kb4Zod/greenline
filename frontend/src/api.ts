import type {
  Bill,
  Forecast,
  Health,
  ImportBatch,
  ImportReceipt,
} from "./types";

export class ApiError extends Error {
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(`API error ${status}`);
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = (await response.json()).detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/api/health"),
  forecast: () => request<Forecast>("/api/forecast"),
  bills: () => request<Bill[]>("/api/bills"),
  patchBill: (id: number, patch: Partial<Bill>) =>
    request<Bill>(`/api/bills/${id}`, json("PATCH", patch)),
  createBill: (body: {
    account_id: number;
    display_name: string;
    amount_cents: number;
    cadence: string;
    next_due: string;
  }) => request<Bill>("/api/bills", json("POST", body)),
  imports: () => request<ImportBatch[]>("/api/imports"),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ImportReceipt>("/api/imports", { method: "POST", body: form });
  },
};
