/**
 * Clientes tipados para `/api/friends/{id}/interactions`.
 */

import { api } from "./api";
import type { Interaction, InteractionCreatePayload } from "../types";

export const interactionsApi = {
  list: (friendId: number) =>
    api.get<Interaction[]>(`/friends/${friendId}/interactions`),
  create: (friendId: number, payload: InteractionCreatePayload) =>
    api.post<Interaction>(`/friends/${friendId}/interactions`, payload),
};
