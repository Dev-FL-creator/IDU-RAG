import { SearchResult } from "@/lib/api"

export interface Company {
  id: string
  name: string
  icon: string // URL to company logo/icon
  shortDescription: string
  fullDescription: string
  industry?: string
  founded?: string
  location?: string
  website?: string
  images: CompanyImage[]
  metrics?: CompanyMetric[]
  searchResult?: SearchResult // 添加搜索结果数据
}

export interface CompanyImage {
  url: string
  alt: string
  caption?: string
}

export interface CompanyMetric {
  label: string
  value: string
  trend?: "up" | "down" | "neutral"
}
