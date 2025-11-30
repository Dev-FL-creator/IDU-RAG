"use client"

import { SearchResult } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Building2, Globe, Users, MapPin, Calendar, Phone, Mail, Award, Wrench, FolderOpen, User, Hash } from "lucide-react"

interface StructuredCompanyInfoProps {
  searchResult: SearchResult
}

export function StructuredCompanyInfo({ searchResult }: StructuredCompanyInfoProps) {
  const renderSection = (title: string, icon: React.ReactNode, content: React.ReactNode) => {
    if (!content || (Array.isArray(content) && content.length === 0) || (typeof content === 'string' && !content.trim())) {
      return null
    }

    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          {icon}
          <h4 className="font-medium text-sm">{title}</h4>
        </div>
        <div className="pl-6">
          {content}
        </div>
      </div>
    )
  }

  const renderList = (items: string[] | undefined, type: 'badge' | 'text' = 'text') => {
    if (!items || items.length === 0) return null
    
    if (type === 'badge') {
      return (
        <div className="flex flex-wrap gap-1">
          {items.map((item, idx) => (
            <Badge key={idx} variant="outline" className="text-xs">
              {item}
            </Badge>
          ))}
        </div>
      )
    }
    
    return (
      <ul className="space-y-1">
        {items.map((item, idx) => (
          <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
            <span className="w-1.5 h-1.5 bg-primary rounded-full mt-1.5 flex-shrink-0" />
            {item}
          </li>
        ))}
      </ul>
    )
  }

  return (
    <div className="space-y-4">
      {/* Summary Block with Bold Fields */}
      <div className="p-4 border rounded bg-muted/50 mb-2">
        <div className="mb-1 text-base font-semibold">
          {searchResult.org_name && <span>{searchResult.org_name} </span>}
          {searchResult.country && <span>({searchResult.country}) </span>}
          {searchResult.industry && <span>- {searchResult.industry}</span>}
        </div>
        {searchResult.combined_score !== undefined && (
          <div className="mb-1"><strong>Score:</strong> {typeof searchResult.combined_score === 'number' ? (searchResult.combined_score * 100).toFixed(1) + '%' : searchResult.combined_score}</div>
        )}
        {searchResult.capabilities && searchResult.capabilities.length > 0 && (
          <div className="mb-1"><strong>Capabilities:</strong> {Array.isArray(searchResult.capabilities) ? searchResult.capabilities.join(', ') : searchResult.capabilities}</div>
        )}
        {searchResult.content && (
          <div className="mb-1"><strong>Content:</strong> {searchResult.content}</div>
        )}
      </div>
      {/* Basic Information */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Organization Details</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {renderSection(
            "Industry",
            <Hash className="h-4 w-4 text-muted-foreground" />,
            searchResult.industry && (
              <Badge variant="secondary">{searchResult.industry}</Badge>
            )
          )}

          {renderSection(
            "Location", 
            <MapPin className="h-4 w-4 text-muted-foreground" />,
            (searchResult.country || searchResult.address) && (
              <div className="text-sm text-muted-foreground">
                {searchResult.country && <div>{searchResult.country}</div>}
                {searchResult.address && <div>{searchResult.address}</div>}
              </div>
            )
          )}

          {renderSection(
            "Founded",
            <Calendar className="h-4 w-4 text-muted-foreground" />,
            searchResult.founded_year && (
              <span className="text-sm text-muted-foreground">{searchResult.founded_year}</span>
            )
          )}

          {renderSection(
            "Size",
            <Users className="h-4 w-4 text-muted-foreground" />,
            searchResult.size && (
              <span className="text-sm text-muted-foreground">{searchResult.size}</span>
            )
          )}

          {renderSection(
            "Website",
            <Globe className="h-4 w-4 text-muted-foreground" />,
            searchResult.website && (
              <a 
                href={searchResult.website} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline"
              >
                {searchResult.website}
              </a>
            )
          )}

          {searchResult.is_DU_member && (
            <div className="flex items-center gap-2">
              <Award className="h-4 w-4 text-muted-foreground" />
              <Badge variant="default">DU Member</Badge>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Capabilities & Services */}
      {(searchResult.capabilities || searchResult.services) && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Wrench className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Capabilities & Services</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {renderSection(
              "Capabilities",
              <Wrench className="h-4 w-4 text-muted-foreground" />,
              renderList(searchResult.capabilities, 'badge')
            )}

            {renderSection(
              "Services",
              <FolderOpen className="h-4 w-4 text-muted-foreground" />,
              renderList(searchResult.services, 'badge')
            )}
          </CardContent>
        </Card>
      )}

      {/* Projects & Awards */}
      {(searchResult.projects || searchResult.awards) && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Award className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Projects & Achievements</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {renderSection(
              "Projects",
              <FolderOpen className="h-4 w-4 text-muted-foreground" />,
              renderList(searchResult.projects)
            )}

            {renderSection(
              "Awards",
              <Award className="h-4 w-4 text-muted-foreground" />,
              renderList(searchResult.awards)
            )}
          </CardContent>
        </Card>
      )}

      {/* Contact Information */}
      {(searchResult.contacts_name || searchResult.contacts_email || searchResult.contacts_phone || searchResult.members_name) && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <User className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Contact Information</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {renderSection(
              "Primary Contact",
              <User className="h-4 w-4 text-muted-foreground" />,
              (searchResult.contacts_name || searchResult.contacts_email || searchResult.contacts_phone) && (
                <div className="space-y-2">
                  {searchResult.contacts_name && (
                    <div className="text-sm font-medium">{searchResult.contacts_name}</div>
                  )}
                  {searchResult.contacts_email && (
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <a 
                        href={`mailto:${searchResult.contacts_email}`}
                        className="text-sm text-primary hover:underline"
                      >
                        {searchResult.contacts_email}
                      </a>
                    </div>
                  )}
                  {searchResult.contacts_phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">{searchResult.contacts_phone}</span>
                    </div>
                  )}
                </div>
              )
            )}

            {renderSection(
              "Key Personnel",
              <Users className="h-4 w-4 text-muted-foreground" />,
              (searchResult.members_name || searchResult.members_title || searchResult.members_role) && (
                <div className="space-y-1">
                  {searchResult.members_name && (
                    <div className="text-sm font-medium">{searchResult.members_name}</div>
                  )}
                  {searchResult.members_title && (
                    <div className="text-sm text-muted-foreground">{searchResult.members_title}</div>
                  )}
                  {searchResult.members_role && (
                    <div className="text-sm text-muted-foreground">{searchResult.members_role}</div>
                  )}
                </div>
              )
            )}
          </CardContent>
        </Card>
      )}

      {/* Facilities */}
      {(searchResult.facilities_name || searchResult.facilities_type || searchResult.facilities_usage) && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Facilities</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {searchResult.facilities_name && (
                <div className="text-sm font-medium">{searchResult.facilities_name}</div>
              )}
              {searchResult.facilities_type && (
                <div className="text-sm text-muted-foreground">Type: {searchResult.facilities_type}</div>
              )}
              {searchResult.facilities_usage && (
                <div className="text-sm text-muted-foreground">Usage: {searchResult.facilities_usage}</div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Additional Notes */}
      {searchResult.notes && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Additional Information</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{searchResult.notes}</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}