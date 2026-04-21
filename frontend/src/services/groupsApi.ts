/**
 * Clientes tipados para `/api/groups/*`.
 */

import { api } from "./api";
import type {
  BulkOpResult,
  Friend,
  Group,
  GroupCreatePayload,
  GroupUpdatePayload,
} from "../types";

export const groupsApi = {
  list: () => api.get<Group[]>("/groups"),
  get: (id: number) => api.get<Group>(`/groups/${id}`),
  create: (payload: GroupCreatePayload) => api.post<Group>("/groups", payload),
  update: (id: number, payload: GroupUpdatePayload) =>
    api.patch<Group>(`/groups/${id}`, payload),
  remove: (id: number) => api.del<void>(`/groups/${id}`),

  // ── Membership ──────────────────────────────────────────────
  listMembers: (id: number) => api.get<Friend[]>(`/groups/${id}/members`),
  addMember: (id: number, friendId: number) =>
    api.post<void>(`/groups/${id}/members`, { friend_id: friendId }),
  removeMember: (id: number, friendId: number) =>
    api.del<void>(`/groups/${id}/members/${friendId}`),

  // ── Bulk ────────────────────────────────────────────────────
  bulkAdd: (id: number, friendIds: number[]) =>
    api.post<BulkOpResult>(`/groups/${id}/members/bulk/add`, {
      friend_ids: friendIds,
    }),
  bulkRemove: (id: number, friendIds: number[]) =>
    api.post<BulkOpResult>(`/groups/${id}/members/bulk/remove`, {
      friend_ids: friendIds,
    }),
};
