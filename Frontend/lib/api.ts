const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';

// =============================================================================
// Type Definitions (matching backend schemas)
// =============================================================================

// User types
export interface User {
  id: string;
  email: string;
  username?: string;
  created_at: string;
  is_active: boolean;
}

export interface UserRegisterRequest {
  email: string;
  password: string;
  username?: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

// Project types
export interface Project {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  sort_order: number;
  conversation_count?: number;
}

export interface ProjectCreateRequest {
  user_id: string;
  name: string;
  description?: string;
  icon?: string;
  color?: string;
}

// Conversation types
export interface Conversation {
  id: string;
  user_id: string;
  project_id?: string;
  title: string;
  summary?: string;
  created_at: string;
  updated_at: string;
  last_message_at?: string;
  message_count: number;
  is_pinned: boolean;
  is_archived: boolean;
  last_message_preview?: string;
  project_name?: string;
}

export interface ConversationCreateRequest {
  user_id: string;
  project_id?: string;
  title?: string;
}

// Message types
export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  updated_at?: string;
  is_edited: boolean;
  metadata?: Record<string, unknown>;
  model?: string;
  feedback?: 'positive' | 'negative';
}

export interface MessageCreateRequest {
  user_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  model?: string;
  metadata?: Record<string, unknown>;
}

// API Response types
export interface ApiResponse<T> {
  status: 'ok' | 'error';
  message?: string;
  data?: T;
}

// =============================================================================
// Auth API
// =============================================================================

export class AuthAPI {
  static async register(data: UserRegisterRequest): Promise<{ status: string; user: User; message: string }> {
    const res = await fetch(`${BACKEND_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Registration failed');
    return result;
  }

  static async login(data: UserLoginRequest): Promise<{ status: string; user: User; message: string }> {
    const res = await fetch(`${BACKEND_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Login failed');
    return result;
  }

  static async getUser(userId: string): Promise<{ status: string; user: User }> {
    const res = await fetch(`${BACKEND_URL}/auth/user/${userId}`);
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to get user');
    return result;
  }

  static async checkEmail(email: string): Promise<{ exists: boolean }> {
    const res = await fetch(`${BACKEND_URL}/auth/check-email?email=${encodeURIComponent(email)}`);
    return res.json();
  }
}

// =============================================================================
// Project API
// =============================================================================

export class ProjectAPI {
  static async list(userId: string): Promise<{ status: string; projects: Project[]; total: number; ungrouped_count: number }> {
    const res = await fetch(`${BACKEND_URL}/projects?user_id=${userId}`);
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to list projects');
    return result;
  }

  static async create(data: ProjectCreateRequest): Promise<{ status: string; project: Project; message: string }> {
    const res = await fetch(`${BACKEND_URL}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to create project');
    return result;
  }

  static async get(projectId: string, userId: string): Promise<{ status: string; project: Project }> {
    const res = await fetch(`${BACKEND_URL}/projects/${projectId}?user_id=${userId}`);
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to get project');
    return result;
  }

  static async update(projectId: string, userId: string, data: Partial<Project>): Promise<{ status: string; project: Project; message: string }> {
    const res = await fetch(`${BACKEND_URL}/projects/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, ...data }),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to update project');
    return result;
  }

  static async delete(projectId: string, userId: string): Promise<{ status: string; message: string; conversations_moved: number }> {
    const res = await fetch(`${BACKEND_URL}/projects/${projectId}?user_id=${userId}`, {
      method: 'DELETE',
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to delete project');
    return result;
  }
}

// =============================================================================
// Conversation API
// =============================================================================

export class ConversationAPI {
  static async list(userId: string, projectId?: string): Promise<{ status: string; conversations: Conversation[]; total: number }> {
    let url = `${BACKEND_URL}/conversations?user_id=${userId}`;
    if (projectId) url += `&project_id=${projectId}`;
    const res = await fetch(url);
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to list conversations');
    return result;
  }

  static async create(data: ConversationCreateRequest): Promise<{ status: string; conversation: Conversation; message: string }> {
    const res = await fetch(`${BACKEND_URL}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to create conversation');
    return result;
  }

  static async get(conversationId: string, userId: string): Promise<{ status: string; conversation: Conversation; messages: Message[] }> {
    const res = await fetch(`${BACKEND_URL}/conversations/${conversationId}?user_id=${userId}`);
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to get conversation');
    return result;
  }

  static async update(conversationId: string, userId: string, data: { title?: string; is_pinned?: boolean; is_archived?: boolean }): Promise<{ status: string; conversation: Conversation; message: string }> {
    const res = await fetch(`${BACKEND_URL}/conversations/${conversationId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, ...data }),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to update conversation');
    return result;
  }

  static async delete(conversationId: string, userId: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`${BACKEND_URL}/conversations/${conversationId}?user_id=${userId}`, {
      method: 'DELETE',
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to delete conversation');
    return result;
  }

  static async move(conversationId: string, userId: string, projectId: string | null): Promise<{ status: string; message: string; conversation_id: string; old_project_id?: string; new_project_id?: string }> {
    const res = await fetch(`${BACKEND_URL}/conversations/${conversationId}/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, project_id: projectId }),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to move conversation');
    return result;
  }

  static async addMessage(conversationId: string, data: MessageCreateRequest): Promise<{ status: string; message_data: Message }> {
    const res = await fetch(`${BACKEND_URL}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to add message');
    return result;
  }

  static async generateTitle(conversation: string): Promise<string> {
    const res = await fetch(`${BACKEND_URL}/conversations/generate-title`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation }),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.message || 'Failed to generate title');
    return result.title;
  }
}

// Backend API调用函数

export interface SearchRequest {
  query: string;
  alpha?: number;
  kvec?: number;
  kbm25?: number;
  top_n?: number;
}

export interface SearchResult {
  id: string;
  combined_score: number;
  content: string;
  org_name?: string;
  country?: string;
  address?: string;
  founded_year?: string;
  size?: string;
  industry?: string;
  is_DU_member?: boolean;
  website?: string;
  members_name?: string;
  members_title?: string;
  members_role?: string;
  facilities_name?: string;
  facilities_type?: string;
  facilities_usage?: string;
  capabilities?: string[];
  projects?: string[];
  awards?: string[];
  services?: string[];
  contacts_name?: string;
  contacts_email?: string;
  contacts_phone?: string;
  addresses?: string[];
  notes?: string;
  page_from?: number;
  page_to?: number;
  filepath?: string;
  chunk_index?: number;
}

export interface SearchResponse {
  ok: boolean;
  query: string;
  results: SearchResult[];
}

export class BackendAPI {
  static async hybridSearch(request: SearchRequest): Promise<SearchResponse> {
    const response = await fetch(`${BACKEND_URL}/api/search/hybrid`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Search failed: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }

  static async healthCheck(): Promise<{ ok: boolean; service?: string }> {
    try {
      const response = await fetch(`${BACKEND_URL}/`);
      if (!response.ok) {
        return { ok: false };
      }
      const data = await response.json();
      return {
        ok: true,
        service: data.message || 'Backend running'
      };
    } catch (error) {
      return { ok: false };
    }
  }

  static async uploadPDFs(files: FileList): Promise<any> {
    const formData = new FormData();

    // 添加所有文件
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    // 添加配置参数
    formData.append('chat_model', 'deepseek-chat');
    formData.append('pdf_extraction_method', 'pymupdf');
    formData.append('embedding_dimensions', '1536');

    const response = await fetch(`${BACKEND_URL}/api/upload_pdfs`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`File upload failed: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }

  static async getUploadProgress(jobId: string): Promise<any> {
    const response = await fetch(`${BACKEND_URL}/api/progress/${jobId}`);
    return await response.json();
  }

  // PDF Preview Extraction (without indexing)
  static async extractPDFPreview(files: FileList): Promise<ExtractedDataResponse> {
    const formData = new FormData();

    // 添加所有文件
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    // 添加配置参数
    formData.append('chat_model', 'deepseek-chat');
    formData.append('pdf_extraction_method', 'azure_docint');

    const response = await fetch(`${BACKEND_URL}/api/extract_pdf_preview`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`PDF extraction failed: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }

  // Confirm and Index extracted data
  static async confirmAndIndex(extractedData: ExtractedData[]): Promise<any> {
    const response = await fetch(`${BACKEND_URL}/api/confirm_and_index`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        extracted_data: extractedData,
        embedding_dimensions: 1536,
        batch_upload_size: 64,
        write_action: 'mergeOrUpload'
      }),
    });

    if (!response.ok) {
      throw new Error(`Indexing failed: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }
}

// 添加新的类型定义
export interface Contact {
  name: string;
  email?: string;
  phone?: string;
  title?: string;
  address?: string;
}

export interface Member {
  name: string;
  title?: string;
  role?: string;
}

export interface Facility {
  name: string;
  type?: string;
  usage?: string;
}

export interface ExtractedData {
  filename: string;
  text_length?: number;
  structured_info?: {
    org_name?: string;
    country?: string;
    address?: string;
    founded_year?: number;
    size?: string;
    industry?: string;
    is_DU_member?: boolean;
    website?: string;
    contacts?: Contact[];
    members?: Member[];
    facilities?: Facility[];
    capabilities?: string[];
    projects?: string[];
    awards?: string[];
    services?: string[];
    notes?: string;
    summary?: string;
  };
  raw_text_preview?: string;
  error?: string;
}

export interface ExtractedDataResponse {
  ok: boolean;
  extracted_data: ExtractedData[];
  total_files: number;
}
