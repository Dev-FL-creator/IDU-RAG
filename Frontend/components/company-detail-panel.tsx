"use client"

import { Company } from "@/types/company"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { ImageViewer } from "@/components/image-viewer"
import { StructuredCompanyInfo } from "@/components/structured-company-info"
import { X, ExternalLink, MapPin, Calendar, TrendingUp, TrendingDown, Minus } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface CompanyDetailPanelProps {
  company: Company
  onClose: () => void
}

export function CompanyDetailPanel({ company, onClose }: CompanyDetailPanelProps) {
  return (
    <div className="flex flex-col h-full bg-white border-l">
      {/* Header */}
      <div className="p-6 border-b bg-[#e0f2e9]">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4 flex-1">
            <Avatar className="h-16 w-16 rounded-xl border-2 border-primary/20">
              <AvatarImage src={company.icon} alt={company.name} />
              <AvatarFallback className="text-lg font-semibold rounded-xl">
                {company.name.substring(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <h2 className="text-2xl font-bold">{company.name}</h2>
              {company.industry && (
                <Badge variant="secondary" className="mt-2">
                  {company.industry}
                </Badge>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="shrink-0"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Quick Info */}
        <div className="flex flex-wrap gap-4 mt-4 text-sm text-muted-foreground">
          {company.location && (
            <div className="flex items-center gap-1">
              <MapPin className="h-4 w-4" />
              {company.location}
            </div>
          )}
          {company.founded && (
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              Founded {company.founded}
            </div>
          )}
          {company.website && (
            <a
              href={company.website}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-primary transition-colors"
            >
              <ExternalLink className="h-4 w-4" />
              Website
            </a>
          )}
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Structured Company Information */}
          {company.searchResult ? (
            <>
              <div>
                <h3 className="text-lg font-semibold mb-3">About</h3>
                <StructuredCompanyInfo searchResult={company.searchResult} />
              </div>
            </>
          ) : (
            <>
              {/* Fallback to simple description */}
              <div>
                <h3 className="text-lg font-semibold mb-3">About</h3>
                <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">
                  {company.fullDescription}
                </p>
              </div>

              <Separator />
            </>
          )}

          {/* Metrics */}
          {company.metrics && company.metrics.length > 0 && (
            <>
              <div>
                <h3 className="text-lg font-semibold mb-3">Key Metrics</h3>
                <div className="grid grid-cols-2 gap-4">
                  {company.metrics.map((metric, idx) => (
                    <Card key={idx} className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">
                            {metric.label}
                          </p>
                          <p className="text-xl font-bold">{metric.value}</p>
                        </div>
                        {metric.trend && (
                          <div>
                            {metric.trend === "up" && (
                              <TrendingUp className="h-5 w-5 text-green-500" />
                            )}
                            {metric.trend === "down" && (
                              <TrendingDown className="h-5 w-5 text-red-500" />
                            )}
                            {metric.trend === "neutral" && (
                              <Minus className="h-5 w-5 text-muted-foreground" />
                            )}
                          </div>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
              <Separator />
            </>
          )}

          {/* Images */}
          {company.images && company.images.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Gallery</h3>
              <div className="grid grid-cols-1 gap-4">
                {company.images.map((image, idx) => (
                  <div key={idx}>
                    <Card className="p-3 overflow-hidden">
                      <ImageViewer src={image.url} alt={image.alt} />
                      {image.caption && (
                        <p className="text-xs text-muted-foreground mt-2">
                          {image.caption}
                        </p>
                      )}
                    </Card>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
