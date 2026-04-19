/**
 * Clientes tipados para `/api/interests` e `/api/friends/{id}/tags`.
 */

import { api } from "./api";
import type { Friend, InterestSummary } from "../types";

export const interestsApi = {
  list: () => api.get<InterestSummary[]>("/interests"),
  addTag: (friendId: number, tag: string) =>
    api.post<Friend>(`/friends/${friendId}/tags`, { tag }),
  removeTag: (friendId: number, tag: string) =>
    api.del<Friend>(`/friends/${friendId}/tags/${encodeURIComponent(tag)}`),
};
