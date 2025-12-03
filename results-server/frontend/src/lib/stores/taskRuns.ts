/**
 * Task runs store with filters and pagination
 */

import { writable, derived } from 'svelte/store';
import { api, type TaskRunSummary, type TaskRunQueryParams } from '$lib/api/client';

export interface TaskRunsState {
  items: TaskRunSummary[];
  total: number;
  page: number;
  perPage: number;
  pages: number;
  loading: boolean;
  error: string | null;
}

export interface FiltersState {
  system: string[];
  architecture: string;
  benchmarkLabel: string;
  nodeCountMin: number | null;
  nodeCountMax: number | null;
  status: string;
  submittedAfter: string;
  submittedBefore: string;
  primaryFomName: string;
}

// Initial states
const initialTaskRuns: TaskRunsState = {
  items: [],
  total: 0,
  page: 1,
  perPage: 50,
  pages: 0,
  loading: false,
  error: null,
};

const initialFilters: FiltersState = {
  system: [],
  architecture: '',
  benchmarkLabel: '',
  nodeCountMin: null,
  nodeCountMax: null,
  status: '',
  submittedAfter: '',
  submittedBefore: '',
  primaryFomName: '',
};

// Stores
export const taskRuns = writable<TaskRunsState>(initialTaskRuns);
export const filters = writable<FiltersState>(initialFilters);

// Actions
export async function fetchTaskRuns(page = 1, perPage = 50) {
  taskRuns.update(s => ({ ...s, loading: true, error: null }));

  try {
    let currentFilters: FiltersState = initialFilters;
    filters.subscribe(f => currentFilters = f)();

    const params: TaskRunQueryParams = {
      page,
      per_page: perPage,
    };

    if (currentFilters.system.length) params.system = currentFilters.system;
    if (currentFilters.architecture) params.architecture = currentFilters.architecture;
    if (currentFilters.benchmarkLabel) params.benchmark_label = currentFilters.benchmarkLabel;
    if (currentFilters.nodeCountMin) params.node_count_min = currentFilters.nodeCountMin;
    if (currentFilters.nodeCountMax) params.node_count_max = currentFilters.nodeCountMax;
    if (currentFilters.status) params.status = currentFilters.status;
    if (currentFilters.submittedAfter) params.submitted_after = currentFilters.submittedAfter;
    if (currentFilters.submittedBefore) params.submitted_before = currentFilters.submittedBefore;
    if (currentFilters.primaryFomName) params.primary_fom_name = currentFilters.primaryFomName;

    const response = await api.listTaskRuns(params);

    taskRuns.set({
      items: response.items,
      total: response.total,
      page: response.page,
      perPage: response.per_page,
      pages: response.pages,
      loading: false,
      error: null,
    });
  } catch (err) {
    taskRuns.update(s => ({
      ...s,
      loading: false,
      error: err instanceof Error ? err.message : 'Failed to fetch task runs',
    }));
  }
}

export function updateFilters(newFilters: Partial<FiltersState>) {
  filters.update(f => ({ ...f, ...newFilters }));
}

export function resetFilters() {
  filters.set(initialFilters);
}

// Derived stores
export const hasActiveFilters = derived(filters, $filters => {
  return (
    $filters.system.length > 0 ||
    $filters.architecture !== '' ||
    $filters.benchmarkLabel !== '' ||
    $filters.nodeCountMin !== null ||
    $filters.nodeCountMax !== null ||
    $filters.status !== '' ||
    $filters.submittedAfter !== '' ||
    $filters.submittedBefore !== ''
  );
});

