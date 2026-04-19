/**
 * Clientes tipados para `/api/dashboard/*`.
 */

import { api } from "./api";
import type {
  DashboardClustersResponse,
  DashboardOverdueResponse,
  DashboardSummary,
} from "../types";

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>("/dashboard/summary"),
  overdue: () => api.get<DashboardOverdueResponse>("/dashboard/overdue"),
  clusters: () => api.get<DashboardClustersResponse>("/dashboard/clusters"),
};
