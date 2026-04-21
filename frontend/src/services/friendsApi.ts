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
  MergeResult,
} from "../types";

export type FriendListFilters = {
  category?: Category;
  cadence?: Cadence;
  tag?: string;
  group_id?: number;
  /** Quando true, devolve so amigos que nao pertencem a nenhum grupo. */
  no_group?: boolean;
};

function toQueryString(filters: FriendListFilters): string {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.cadence) params.set("cadence", filters.cadence);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.group_id) params.set("group_id", String(filters.group_id));
  if (filters.no_group) params.set("no_group", "true");
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
  bulkMerge: (primary_id: number, source_ids: number[]) =>
    api.post<MergeResult>("/friends/bulk/merge", { primary_id, source_ids }),
  bulkAddGroup: (ids: number[], group_id: number) =>
    api.post<BulkOpResult>("/friends/bulk/groups/add", { ids, group_id }),
  bulkRemoveGroup: (ids: number[], group_id: number) =>
    api.post<BulkOpResult>("/friends/bulk/groups/remove", { ids, group_id }),
};
