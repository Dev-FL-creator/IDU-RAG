"use client"

import { Card } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { ChevronRight } from "lucide-react"
import { Company } from "@/types/company"
import { cn } from "@/lib/utils"

interface CompanyCardProps {
  company: Company
  onClick: () => void
  className?: string
}

export function CompanyCard({ company, onClick, className }: CompanyCardProps) {
  return (
    <Card
      className={cn(
        "p-4 cursor-pointer hover:shadow-lg transition-all hover:border-primary/50 group bg-white",
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-start gap-4">
        {/* Company Icon */}
        <Avatar className="h-16 w-16 rounded-full border-2 border-muted">
          <AvatarImage src={company.icon} alt={company.name} />
          <AvatarFallback className="text-lg font-semibold">
            {company.name.substring(0, 2).toUpperCase()}
          </AvatarFallback>
        </Avatar>

        {/* Company Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold text-base line-clamp-1">
              {company.name}
            </h3>
            <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
          </div>

          {company.industry && (
            <p className="text-xs text-muted-foreground mt-1">
              {company.industry}
            </p>
          )}

          <p className="text-sm text-foreground/80 mt-2 line-clamp-2">
            {company.shortDescription}
          </p>

          {/* Quick Metrics */}
          {company.metrics && company.metrics.length > 0 && (
            <div className="flex gap-4 mt-3">
              {company.metrics.slice(0, 2).map((metric, idx) => (
                <div key={idx} className="text-xs">
                  <span className="text-muted-foreground">{metric.label}:</span>{" "}
                  <span className="font-semibold">{metric.value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}
