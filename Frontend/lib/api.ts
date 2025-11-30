// 聊天记录API
export interface ChatMessage {
  user_id: string;
  role: string; // 'user' | 'assistant'
  content: string;
  timestamp?: string;
  conversation_id?: string;
}

export class ChatAPI {

  // 生成对话标题（调用 deepseek 后端接口）
  static async generateTitle(conversation: string): Promise<string> {
    const res = await fetch(`${BACKEND_URL}/chat/generate_title`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation }),
    });
    if (!res.ok) throw new Error('Failed to generate title');
    const data = await res.json();
    if (data && data.title) return data.title;
    throw new Error('No title returned');
  }
  static async saveChatMessage(message: ChatMessage) {
    await fetch(`${BACKEND_URL}/chat/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(message),
    });
  }

  static async fetchChatHistory(userId: string): Promise<ChatMessage[]> {
    const res = await fetch(`${BACKEND_URL}/chat/history?user_id=${userId}`);
    if (!res.ok) throw new Error('Failed to fetch chat history');
    return res.json();
  }

    // 重命名会话
    static async renameConversation(conversationId: string, newTitle: string) {
      const res = await fetch(`${BACKEND_URL}/chat/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId, new_title: newTitle }),
      });
      if (!res.ok) throw new Error('Failed to rename conversation');
      return res.json();
    }

  // Fetch messages for a specific conversation
  static async fetchConversationMessages(conversationId: string): Promise<ChatMessage[]> {
    const res = await fetch(`${BACKEND_URL}/chat/conversation?conversation_id=${conversationId}`);
    if (!res.ok) throw new Error('Failed to fetch conversation messages');
    return res.json();
  }

  // 删除会话
  static async deleteConversation(conversationId: string) {
    const res = await fetch(`${BACKEND_URL}/chat/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: conversationId }),
    });
    if (!res.ok) throw new Error('Failed to delete conversation');
    return res.json();
  }

  // 移动会话到项目
  static async moveConversationToProject(conversationId: string, projectId: string) {
    const res = await fetch(`${BACKEND_URL}/chat/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: conversationId, project_id: projectId }),
    });
    if (!res.ok) throw new Error('Failed to move conversation');
    return res.json();
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

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

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