/**
 * API client for BenchPRO Results Server
 */

// Use relative URL to work with Vite proxy in dev, or direct in production
const API_BASE = '/api/v1';

export interface ApiError {
  error: string;
  message: string;
  details?: { field?: string; message: string }[];
}

export class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async fetch<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        error: 'unknown_error',
        message: response.statusText,
      }));
      throw error;
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Health
  async health() {
    return this.fetch<{ status: string; version: string; app_name: string }>('/health');
  }

  // Task Runs
  async listTaskRuns(params: TaskRunQueryParams = {}) {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.per_page) query.set('per_page', String(params.per_page));
    if (params.system?.length) params.system.forEach(s => query.append('system', s));
    if (params.architecture) query.set('architecture', params.architecture);
    if (params.benchmark_label) query.set('benchmark_label', params.benchmark_label);
    if (params.node_count_min) query.set('node_count_min', String(params.node_count_min));
    if (params.node_count_max) query.set('node_count_max', String(params.node_count_max));
    if (params.status) query.set('status', params.status);
    if (params.submitted_after) query.set('submitted_after', params.submitted_after);
    if (params.submitted_before) query.set('submitted_before', params.submitted_before);
    if (params.primary_fom_name) query.set('primary_fom_name', params.primary_fom_name);

    const queryString = query.toString();
    return this.fetch<PaginatedResponse<TaskRunSummary>>(
      `/task_runs${queryString ? `?${queryString}` : ''}`
    );
  }

  async getTaskRun(id: number) {
    return this.fetch<TaskRunDetail>(`/task_runs/${id}`);
  }

  async getTaskProvenance(id: number) {
    return this.fetch<TaskProvenance>(`/task_runs/${id}/provenance`);
  }

  async getArtifactText(id: number, maxBytes?: number) {
    const query = maxBytes ? `?mode=text&max_bytes=${maxBytes}` : '?mode=text';
    return this.fetch<ArtifactContent>(`/provenance_artifacts/${id}${query}`);
  }

  // Applications
  async listApplications(params: { q?: string; page?: number; per_page?: number } = {}) {
    const query = new URLSearchParams();
    if (params.q) query.set('q', params.q);
    if (params.page) query.set('page', String(params.page));
    if (params.per_page) query.set('per_page', String(params.per_page));

    const queryString = query.toString();
    return this.fetch<PaginatedResponse<Application>>(
      `/applications${queryString ? `?${queryString}` : ''}`
    );
  }

  // Benchmark Definitions
  async listBenchmarkDefinitions(params: { q?: string; page?: number; per_page?: number } = {}) {
    const query = new URLSearchParams();
    if (params.q) query.set('q', params.q);
    if (params.page) query.set('page', String(params.page));
    if (params.per_page) query.set('per_page', String(params.per_page));

    const queryString = query.toString();
    return this.fetch<PaginatedResponse<BenchmarkDefinition>>(
      `/benchmark_definitions${queryString ? `?${queryString}` : ''}`
    );
  }

  // Saved Views
  async listSavedViews(scope: 'mine' | 'shared' | 'all' = 'all') {
    return this.fetch<SavedViewSummary[]>(`/saved_views?scope=${scope}`);
  }

  async createSavedView(data: CreateSavedView) {
    return this.fetch<SavedViewDetail>('/saved_views', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getSavedView(id: number) {
    return this.fetch<SavedViewDetail>(`/saved_views/${id}`);
  }

  async deleteSavedView(id: number) {
    return this.fetch<void>(`/saved_views/${id}`, { method: 'DELETE' });
  }

  // API Tokens
  async listTokens() {
    return this.fetch<{ tokens: ApiToken[] }>('/api_tokens');
  }

  async createToken(name: string) {
    return this.fetch<ApiTokenCreated>('/api_tokens', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async revokeToken(id: number) {
    return this.fetch<void>(`/api_tokens/${id}`, { method: 'DELETE' });
  }
}

// Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface TaskRunQueryParams {
  page?: number;
  per_page?: number;
  system?: string[];
  architecture?: string;
  benchmark_label?: string;
  node_count_min?: number;
  node_count_max?: number;
  status?: string;
  submitted_after?: string;
  submitted_before?: string;
  primary_fom_name?: string;
}

export interface TaskRunSummary {
  id: number;
  task_uuid: string;
  label: string;
  system: string;
  architecture?: string;
  node_count?: number;
  runtime_seconds?: number;
  status: string;
  submit_time: string;
  user?: { id: number; external_id: string; display_name?: string };
  primary_fom?: FigureOfMerit;
}

export interface TaskRunDetail extends TaskRunSummary {
  user_id: number;
  benchmark_definition_id?: number;
  application_id?: number;
  start_time?: string;
  end_time?: string;
  benchpro_version?: string;
  extra?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  application?: Application;
  benchmark_definition?: BenchmarkDefinition;
  figures_of_merit: FigureOfMerit[];
}

export interface FigureOfMerit {
  name: string;
  value: number | string | null;
  unit?: string;
  value_type: 'numeric' | 'string';
  is_primary: boolean;
}

export interface Application {
  id: number;
  label: string;
  version?: string;
  system?: string;
  architecture?: string;
  modules?: string[];
  benchpro_version?: string;
  build_user?: string;
  build_time?: string;
  extra?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface BenchmarkDefinition {
  id: number;
  label: string;
  description?: string;
  default_primary_fom_name?: string;
  fom_schema?: Record<string, unknown>;
  extra?: Record<string, unknown>;
  application_id?: number;
  created_at: string;
  updated_at: string;
}

export interface TaskProvenance {
  metadata: ProvenanceMetadata[];
  artifacts: ProvenanceArtifact[];
  modules?: string[];
  environment?: Record<string, string>;
  scheduler?: Record<string, unknown>;
  git_commit?: string;
}

export interface ProvenanceMetadata {
  id: number;
  task_run_id: number;
  key: string;
  value_text?: string;
  value_json?: Record<string, unknown>;
}

export interface ProvenanceArtifact {
  id: number;
  task_run_id: number;
  name: string;
  content_type: string;
  encoding: string;
  size_bytes: number;
  created_at: string;
}

export interface ArtifactContent {
  id: number;
  name: string;
  content_type: string;
  encoding: string;
  size_bytes: number;
  content?: string;
  truncated: boolean;
}

export interface SavedViewSummary {
  id: number;
  name: string;
  description?: string;
  visibility: 'private' | 'public';
  owner?: { id: number; external_id: string; display_name?: string };
  created_at: string;
  updated_at: string;
}

export interface SavedViewDetail extends SavedViewSummary {
  owner_user_id: number;
  config: SavedViewConfig;
}

export interface SavedViewConfig {
  filters?: Record<string, unknown>;
  primary_fom_name?: string;
  visible_columns?: string[];
  chart_type?: string;
  chart_x_axis?: string;
  chart_y_axis?: string;
}

export interface CreateSavedView {
  name: string;
  description?: string;
  visibility: 'private' | 'public';
  config: SavedViewConfig;
}

export interface ApiToken {
  id: number;
  name: string;
  created_at: string;
  revoked_at?: string;
}

export interface ApiTokenCreated extends ApiToken {
  token: string;
}

// Singleton instance
export const api = new ApiClient();

