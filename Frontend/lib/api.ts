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
  industry?: string;
  capabilities?: string[];
  projects?: string[];
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
      throw new Error(`搜索失败: ${response.status} ${response.statusText}`);
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
      throw new Error(`文件上传失败: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }

  static async getUploadProgress(jobId: string): Promise<any> {
    const response = await fetch(`${BACKEND_URL}/api/progress/${jobId}`);
    return await response.json();
  }
}