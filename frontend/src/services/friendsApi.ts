/**
 * Clientes tipados para `/api/friends/*`.
 */

import { api } from "./api";
import type {
  BulkOpResult,
  Cadence,
  Category,
  Friend,
  FriendCreatePayload,
  FriendUpdatePayload,
} from "../types";

export type FriendListFilters = {
  category?: Category;
  cadence?: Cadence;
  tag?: string;
};

function toQueryString(filters: FriendListFilters): string {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.cadence) params.set("cadence", filters.cadence);
  if (filters.tag) params.set("tag", filters.tag);
  const q = params.toString();
  return q ? `?${q}` : "";
}

export const friendsApi = {
  list: (filters: FriendListFilters = {}) =>
    api.get<Friend[]>(`/friends${toQueryString(filters)}`),
  get: (id: number) => api.get<Friend>(`/friends/${id}`),
  create: (payload: FriendCreatePayload) =>
    api.post<Friend>("/friends", payload),
  update: (id: number, payload: FriendUpdatePayload) =>
    api.patch<Friend>(`/friends/${id}`, payload),
  remove: (id: number) => api.del<void>(`/friends/${id}`),

  // ── Bulk ─────────────────────────────────────────────────────
  bulkDelete: (ids: number[]) =>
    api.post<BulkOpResult>("/friends/bulk/delete", { ids }),
  bulkTouch: (ids: number[]) =>
    api.post<BulkOpResult>("/friends/bulk/touch", { ids }),
  bulkAddTag: (ids: number[], tag: string) =>
    api.post<BulkOpResult>("/friends/bulk/tags/add", { ids, tag }),
  bulkRemoveTag: (ids: number[], tag: string) =>
    api.post<BulkOpResult>("/friends/bulk/tags/remove", { ids, tag }),
};
