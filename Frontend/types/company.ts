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
