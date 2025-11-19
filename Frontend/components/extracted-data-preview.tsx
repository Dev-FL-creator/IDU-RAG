"use client"

import { useState } from "react"
import { Check, Edit2, X, AlertCircle, FileText, Building2, Globe, Wrench, FolderOpen, Users, MapPin, Calendar, Hash, ExternalLink, Award, Settings, StickyNote, User, Mail, Phone } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ExtractedData } from "@/lib/api"

interface ExtractedDataPreviewProps {
  extractedData: ExtractedData[]
  onConfirm: (data: ExtractedData[]) => void
  onCancel: () => void
  isConfirming?: boolean
}

export function ExtractedDataPreview({ 
  extractedData, 
  onConfirm, 
  onCancel, 
  isConfirming = false 
}: ExtractedDataPreviewProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editData, setEditData] = useState<ExtractedData[]>(extractedData)
  const [selectedFiles, setSelectedFiles] = useState<boolean[]>(
    extractedData.map(item => !item.error)
  )

  const handleEdit = (index: number) => {
    setEditingIndex(index)
  }

  const handleSave = (index: number) => {
    setEditingIndex(null)
  }

  const handleCancel = (index: number) => {
    setEditData(prev => {
      const newData = [...prev]
      newData[index] = extractedData[index]
      return newData
    })
    setEditingIndex(null)
  }

  const updateField = (index: number, field: keyof NonNullable<ExtractedData['structured_info']>, value: any) => {
    setEditData(prev => {
      const newData = [...prev]
      if (!newData[index].structured_info) {
        newData[index].structured_info = {}
      }
      (newData[index].structured_info as any)[field] = value
      return newData
    })
  }

  const updateArrayField = (index: number, field: 'capabilities' | 'projects' | 'awards' | 'services', value: string) => {
    const arrayValue = value.split('\n').filter(item => item.trim())
    updateField(index, field, arrayValue)
  }

  const validDataCount = editData.filter(item => !item.error).length
  const errorCount = editData.filter(item => item.error).length
  const selectedValidCount = editData.filter((item, index) => selectedFiles[index] && !item.error).length
  const allValidSelected = validDataCount > 0 && selectedValidCount === validDataCount

  const toggleFileSelection = (index: number) => {
    setSelectedFiles(prev => {
      const newSelected = [...prev]
      newSelected[index] = !newSelected[index]
      return newSelected
    })
  }

  const toggleAllValidFiles = () => {
    setSelectedFiles(prev => {
      return editData.map((item, index) => 
        item.error ? false : !allValidSelected
      )
    })
  }

  const handleConfirmSelected = () => {
    const selectedData = editData.filter((item, index) => selectedFiles[index] && !item.error)
    onConfirm(selectedData)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Extracted Data Preview</h2>
          <p className="text-sm text-muted-foreground">
            Review and edit the extracted information from {editData.length} PDF file{editData.length !== 1 ? 's' : ''} before indexing
          </p>
        </div>
        <div className="flex items-center gap-3">
          {validDataCount > 1 && (
            <Button
              variant="outline"
              size="sm"
              onClick={toggleAllValidFiles}
              className="h-8"
            >
              {allValidSelected ? 'Unselect All' : 'Select All Valid'}
            </Button>
          )}
          <Badge variant="outline" className="text-xs">
            {editData.length} Files
          </Badge>
          <Badge variant={selectedValidCount > 0 ? "default" : "secondary"}>
            {selectedValidCount} Selected
          </Badge>
          <Badge variant={validDataCount > 0 ? "default" : "secondary"}>
            {validDataCount} Valid
          </Badge>
          {errorCount > 0 && (
            <Badge variant="destructive">
              {errorCount} Errors
            </Badge>
          )}
        </div>
      </div>

      {/* Data Cards */}
      <div className="space-y-4 max-h-96 overflow-y-auto">
        {editData.map((item, index) => (
          <Card key={index} className={item.error ? "border-red-200" : ""}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-primary/10 text-primary rounded-full flex items-center justify-center text-sm font-medium">
                      {index + 1}
                    </div>
                    <FileText className="h-5 w-5 text-red-500" />
                  </div>
                  <CardTitle className="text-lg">{item.filename}</CardTitle>
                </div>
                <div className="flex items-center gap-2">
                  {!item.error && (
                    <input
                      type="checkbox"
                      checked={selectedFiles[index]}
                      onChange={() => toggleFileSelection(index)}
                      className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                  )}
                  {item.text_length && (
                    <Badge variant="outline" className="text-xs">
                      {Math.round(item.text_length / 1000)}k chars
                    </Badge>
                  )}
                  {!item.error && editingIndex !== index && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(index)}
                    >
                      <Edit2 className="h-4 w-4 mr-1" />
                      Edit
                    </Button>
                  )}
                  {editingIndex === index && (
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSave(index)}
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleCancel(index)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </CardHeader>
            
            <CardContent>
              {item.error ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-red-600">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-sm font-medium">{item.error}</span>
                  </div>
                  {item.raw_text_preview && (
                    <div className="mt-3">
                      <label className="text-sm font-medium text-muted-foreground">Extracted Text Preview:</label>
                      <div className="mt-1 p-3 bg-muted/50 rounded text-xs font-mono text-muted-foreground max-h-32 overflow-y-auto">
                        {item.raw_text_preview}
                      </div>
                    </div>
                  )}
                  <div className="text-xs text-muted-foreground">
                    <strong>Troubleshooting:</strong>
                    <ul className="mt-1 ml-4 list-disc space-y-1">
                      <li>If this is a scanned PDF, try using OCR or convert to text first</li>
                      <li>Check if the PDF is password protected</li>
                      <li>Ensure the PDF contains selectable text, not just images</li>
                      <li>Try a different PDF extraction method or manual text input</li>
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Organization Name */}
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <label className="text-sm font-medium w-24">Organization:</label>
                    {editingIndex === index ? (
                      <Input
                        value={item.structured_info?.org_name || ''}
                        onChange={(e) => updateField(index, 'org_name', e.target.value)}
                        className="flex-1"
                        placeholder="Organization name"
                      />
                    ) : (
                      <span className="flex-1 text-sm">
                        {item.structured_info?.org_name || 'Not specified'}
                      </span>
                    )}
                  </div>

                  {/* Country */}
                  <div className="flex items-center gap-2">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <label className="text-sm font-medium w-24">Country:</label>
                    {editingIndex === index ? (
                      <Input
                        value={item.structured_info?.country || ''}
                        onChange={(e) => updateField(index, 'country', e.target.value)}
                        className="flex-1"
                        placeholder="Country"
                      />
                    ) : (
                      <span className="flex-1 text-sm">
                        {item.structured_info?.country || 'Not specified'}
                      </span>
                    )}
                  </div>

                  {/* Industry */}
                  <div className="flex items-center gap-2">
                    <FolderOpen className="h-4 w-4 text-muted-foreground" />
                    <label className="text-sm font-medium w-24">Industry:</label>
                    {editingIndex === index ? (
                      <Input
                        value={item.structured_info?.industry || ''}
                        onChange={(e) => updateField(index, 'industry', e.target.value)}
                        className="flex-1"
                        placeholder="Industry"
                      />
                    ) : (
                      <span className="flex-1 text-sm">
                        {item.structured_info?.industry || 'Not specified'}
                      </span>
                    )}
                  </div>

                  {/* Address */}
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <label className="text-sm font-medium w-24">Address:</label>
                    {editingIndex === index ? (
                      <Textarea
                        value={item.structured_info?.address || ''}
                        onChange={(e) => updateField(index, 'address', e.target.value)}
                        className="flex-1"
                        placeholder="Full address"
                        rows={2}
                      />
                    ) : (
                      <span className="flex-1 text-sm">
                        {item.structured_info?.address || 'Not specified'}
                      </span>
                    )}
                  </div>

                  {/* Founded Year */}
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <label className="text-sm font-medium w-24">Founded:</label>
                    {editingIndex === index ? (
                      <Input
                        type="number"
                        value={item.structured_info?.founded_year || ''}
                        onChange={(e) => updateField(index, 'founded_year', parseInt(e.target.value) || null)}
                        className="flex-1"
                        placeholder="Founded year"
                      />
                    ) : (
                      <span className="flex-1 text-sm">
                        {item.structured_info?.founded_year || 'Not specified'}
                      </span>
                    )}
                  </div>

                  {/* Size */}
                  <div className="flex items-center gap-2">
                    <Hash className="h-4 w-4 text-muted-foreground" />
                    <label className="text-sm font-medium w-24">Size:</label>
                    {editingIndex === index ? (
                      <Input
                        value={item.structured_info?.size || ''}
                        onChange={(e) => updateField(index, 'size', e.target.value)}
                        className="flex-1"
                        placeholder="Organization size"
                      />
                    ) : (
                      <span className="flex-1 text-sm">
                        {item.structured_info?.size || 'Not specified'}
                      </span>
                    )}
                  </div>

                  {/* Website */}
                  <div className="flex items-center gap-2">
                    <ExternalLink className="h-4 w-4 text-muted-foreground" />
                    <label className="text-sm font-medium w-24">Website:</label>
                    {editingIndex === index ? (
                      <Input
                        value={item.structured_info?.website || ''}
                        onChange={(e) => updateField(index, 'website', e.target.value)}
                        className="flex-1"
                        placeholder="Website URL"
                      />
                    ) : (
                      <span className="flex-1 text-sm">
                        {item.structured_info?.website ? (
                          <a href={item.structured_info.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                            {item.structured_info.website}
                          </a>
                        ) : 'Not specified'}
                      </span>
                    )}
                  </div>

                  {/* Capabilities */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Wrench className="h-4 w-4 text-muted-foreground" />
                      <label className="text-sm font-medium">Capabilities:</label>
                    </div>
                    {editingIndex === index ? (
                      <Textarea
                        value={item.structured_info?.capabilities?.join('\n') || ''}
                        onChange={(e) => updateArrayField(index, 'capabilities', e.target.value)}
                        className="min-h-[100px]"
                        placeholder="Enter capabilities, one per line"
                      />
                    ) : (
                      <div className="flex flex-wrap gap-2 ml-6">
                        {item.structured_info?.capabilities?.length ? (
                          item.structured_info.capabilities.map((cap, capIndex) => (
                            <Badge key={capIndex} variant="secondary" className="text-xs">
                              {cap}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-sm text-muted-foreground">No capabilities specified</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Projects */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <FolderOpen className="h-4 w-4 text-muted-foreground" />
                      <label className="text-sm font-medium">Projects:</label>
                    </div>
                    {editingIndex === index ? (
                      <Textarea
                        value={item.structured_info?.projects?.join('\n') || ''}
                        onChange={(e) => updateArrayField(index, 'projects', e.target.value)}
                        className="min-h-[80px]"
                        placeholder="Enter projects, one per line"
                      />
                    ) : (
                      <div className="flex flex-wrap gap-2 ml-6">
                        {item.structured_info?.projects?.length ? (
                          item.structured_info.projects.map((proj, projIndex) => (
                            <Badge key={projIndex} variant="outline" className="text-xs">
                              {proj}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-sm text-muted-foreground">No projects specified</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Awards */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Award className="h-4 w-4 text-muted-foreground" />
                      <label className="text-sm font-medium">Awards:</label>
                    </div>
                    {editingIndex === index ? (
                      <Textarea
                        value={item.structured_info?.awards?.join('\n') || ''}
                        onChange={(e) => updateArrayField(index, 'awards', e.target.value)}
                        className="min-h-[60px]"
                        placeholder="Enter awards, one per line"
                      />
                    ) : (
                      <div className="flex flex-wrap gap-2 ml-6">
                        {item.structured_info?.awards?.length ? (
                          item.structured_info.awards.map((award, awardIndex) => (
                            <Badge key={awardIndex} variant="secondary" className="text-xs">
                              {award}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-sm text-muted-foreground">No awards specified</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Services */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Settings className="h-4 w-4 text-muted-foreground" />
                      <label className="text-sm font-medium">Services:</label>
                    </div>
                    {editingIndex === index ? (
                      <Textarea
                        value={item.structured_info?.services?.join('\n') || ''}
                        onChange={(e) => updateArrayField(index, 'services', e.target.value)}
                        className="min-h-[80px]"
                        placeholder="Enter services, one per line"
                      />
                    ) : (
                      <div className="flex flex-wrap gap-2 ml-6">
                        {item.structured_info?.services?.length ? (
                          item.structured_info.services.map((service, serviceIndex) => (
                            <Badge key={serviceIndex} variant="outline" className="text-xs">
                              {service}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-sm text-muted-foreground">No services specified</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Contacts */}
                  {item.structured_info?.contacts && item.structured_info.contacts.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <label className="text-sm font-medium">Contacts:</label>
                      </div>
                      <div className="ml-6 space-y-3">
                        {item.structured_info.contacts.map((contact, contactIndex) => (
                          <div key={contactIndex} className="border rounded-lg p-3 bg-muted/20">
                            <div className="font-medium text-sm">{contact.name}</div>
                            {contact.title && (
                              <div className="text-xs text-muted-foreground">{contact.title}</div>
                            )}
                            <div className="flex flex-wrap gap-4 mt-1">
                              {contact.email && (
                                <div className="flex items-center gap-1 text-xs">
                                  <Mail className="h-3 w-3" />
                                  <a href={`mailto:${contact.email}`} className="text-blue-600 hover:underline">
                                    {contact.email}
                                  </a>
                                </div>
                              )}
                              {contact.phone && (
                                <div className="flex items-center gap-1 text-xs">
                                  <Phone className="h-3 w-3" />
                                  <span>{contact.phone}</span>
                                </div>
                              )}
                            </div>
                            {contact.address && (
                              <div className="text-xs text-muted-foreground mt-1">{contact.address}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Members */}
                  {item.structured_info?.members && item.structured_info.members.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        <label className="text-sm font-medium">Members:</label>
                      </div>
                      <div className="ml-6 grid grid-cols-1 md:grid-cols-2 gap-2">
                        {item.structured_info.members.map((member, memberIndex) => (
                          <div key={memberIndex} className="border rounded p-2 bg-muted/10">
                            <div className="font-medium text-sm">{member.name}</div>
                            {member.title && (
                              <div className="text-xs text-muted-foreground">{member.title}</div>
                            )}
                            {member.role && (
                              <div className="text-xs text-blue-600">{member.role}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Facilities */}
                  {item.structured_info?.facilities && item.structured_info.facilities.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-muted-foreground" />
                        <label className="text-sm font-medium">Facilities:</label>
                      </div>
                      <div className="ml-6 space-y-2">
                        {item.structured_info.facilities.map((facility, facilityIndex) => (
                          <div key={facilityIndex} className="border-l-2 border-blue-200 pl-3 space-y-2">
                            {editingIndex === index ? (
                              <>
                                <Input
                                  value={facility.name}
                                  onChange={(e) => {
                                    const newFacilities = [...item.structured_info!.facilities!]
                                    newFacilities[facilityIndex] = { ...facility, name: e.target.value }
                                    updateField(index, 'facilities', newFacilities)
                                  }}
                                  placeholder="Facility name"
                                  className="font-medium text-sm"
                                />
                                <Input
                                  value={facility.type || ''}
                                  onChange={(e) => {
                                    const newFacilities = [...item.structured_info!.facilities!]
                                    newFacilities[facilityIndex] = { ...facility, type: e.target.value }
                                    updateField(index, 'facilities', newFacilities)
                                  }}
                                  placeholder="Facility type"
                                  className="text-xs"
                                />
                                <Textarea
                                  value={facility.usage || ''}
                                  onChange={(e) => {
                                    const newFacilities = [...item.structured_info!.facilities!]
                                    newFacilities[facilityIndex] = { ...facility, usage: e.target.value }
                                    updateField(index, 'facilities', newFacilities)
                                  }}
                                  placeholder="Facility usage"
                                  className="text-xs min-h-[60px]"
                                />
                              </>
                            ) : (
                              <>
                                <div className="font-medium text-sm">{facility.name}</div>
                                {facility.type && (
                                  <div className="text-xs text-muted-foreground">Type: {facility.type}</div>
                                )}
                                {facility.usage && (
                                  <div className="text-xs text-muted-foreground">Usage: {facility.usage}</div>
                                )}
                              </>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {item.structured_info?.notes && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <StickyNote className="h-4 w-4 text-muted-foreground" />
                        <label className="text-sm font-medium">Notes:</label>
                      </div>
                      {editingIndex === index ? (
                        <Textarea
                          value={item.structured_info.notes}
                          onChange={(e) => updateField(index, 'notes', e.target.value)}
                          className="min-h-[80px]"
                        />
                      ) : (
                        <p className="text-sm text-muted-foreground bg-muted/30 p-3 rounded ml-6">
                          {item.structured_info.notes}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Summary */}
                  {item.structured_info?.summary && (
                    <>
                      <Separator />
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Summary:</label>
                        {editingIndex === index ? (
                          <Textarea
                            value={item.structured_info.summary}
                            onChange={(e) => updateField(index, 'summary', e.target.value)}
                            className="min-h-[100px]"
                          />
                        ) : (
                          <p className="text-sm text-muted-foreground bg-muted/50 p-3 rounded">
                            {item.structured_info.summary}
                          </p>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button variant="outline" onClick={onCancel} disabled={isConfirming}>
          Cancel
        </Button>
        <Button 
          onClick={handleConfirmSelected} 
          disabled={selectedValidCount === 0 || isConfirming}
          className="min-w-[120px]"
        >
          {isConfirming ? "Indexing..." : `Confirm & Index (${selectedValidCount})`}
        </Button>
      </div>
    </div>
  )
}