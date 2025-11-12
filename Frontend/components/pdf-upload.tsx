"use client"

import { useState, useRef } from "react"
import { Upload, FileText, X, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { BackendAPI, ExtractedData } from "@/lib/api"
import { ExtractedDataPreview } from "./extracted-data-preview"

interface PDFUploadProps {
  onUploadComplete?: (results: any) => void
  disabled?: boolean
}

interface UploadedFile {
  name: string
  size: number
  status: 'pending' | 'uploading' | 'success' | 'error'
  error?: string
}

export function PDFUpload({ onUploadComplete, disabled }: PDFUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null)
  const [extractedData, setExtractedData] = useState<ExtractedData[] | null>(null)
  const [isExtracting, setIsExtracting] = useState(false)
  const [isConfirming, setIsConfirming] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (fileList: FileList) => {
    const newFiles: UploadedFile[] = []
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i]
      if (file.type === 'application/pdf') {
        newFiles.push({
          name: file.name,
          size: file.size,
          status: 'pending'
        })
      }
    }
    setFiles(prev => [...prev, ...newFiles])
    setSelectedFiles(fileList)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const droppedFiles = e.dataTransfer.files
    handleFileSelect(droppedFiles)
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const handleExtractPreview = async () => {
    if (files.length === 0 || isExtracting || !selectedFiles) return

    setIsExtracting(true)
    
    try {
      // 更新所有文件状态为uploading (extracting)
      setFiles(prev => prev.map(f => ({ ...f, status: 'uploading' as const })))

      const response = await BackendAPI.extractPDFPreview(selectedFiles)
      
      // 更新所有文件状态为success
      setFiles(prev => prev.map(f => ({ ...f, status: 'success' as const })))
      
      setExtractedData(response.extracted_data)
      
    } catch (error) {
      console.error('Extraction failed:', error)
      setFiles(prev => prev.map(f => ({ 
        ...f, 
        status: 'error' as const,
        error: error instanceof Error ? error.message : 'Extraction failed'
      })))
    } finally {
      setIsExtracting(false)
    }
  }

  const handleConfirmAndIndex = async (confirmedData: ExtractedData[]) => {
    setIsConfirming(true)
    
    try {
      const response = await BackendAPI.confirmAndIndex(confirmedData)
      onUploadComplete?.(response)
      
      // 重置状态
      setFiles([])
      setSelectedFiles(null)
      setExtractedData(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      
    } catch (error) {
      console.error('Indexing failed:', error)
    } finally {
      setIsConfirming(false)
    }
  }

  const handleCancelPreview = () => {
    setExtractedData(null)
    setFiles([])
    setSelectedFiles(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // 如果有提取的数据，显示预览界面
  if (extractedData) {
    return (
      <ExtractedDataPreview
        extractedData={extractedData}
        onConfirm={handleConfirmAndIndex}
        onCancel={handleCancelPreview}
        isConfirming={isConfirming}
      />
    )
  }

  return (
    <Card className="w-full">
      <CardContent className="p-4">
        <div
          className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 text-center hover:border-muted-foreground/50 transition-colors relative cursor-pointer"
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => !disabled && !isUploading && fileInputRef.current?.click()}
        >
          <div className="flex flex-col items-center gap-2 pointer-events-none">
            <Upload className="h-8 w-8 text-muted-foreground" />
            <div className="text-sm">
              <span className="font-medium">Click to upload</span> or drag and drop PDF files
            </div>
            <div className="text-xs text-muted-foreground">
              PDF files only, max 10MB each
            </div>
          </div>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf"
            className="hidden"
            onChange={(e) => e.target.files && handleFileSelect(e.target.files)}
            disabled={disabled || isUploading}
          />
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            <h4 className="text-sm font-medium">Selected Files:</h4>
            {files.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-2 bg-muted/50 rounded-md"
              >
                <FileText className="h-4 w-4 text-red-500 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{file.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatFileSize(file.size)}
                  </div>
                </div>
                
                {/* Status indicator */}
                <div className="flex items-center gap-2">
                  {file.status === 'uploading' && (
                    <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  )}
                  {file.status === 'success' && (
                    <div className="w-2 h-2 bg-green-500 rounded-full" />
                  )}
                  {file.status === 'error' && (
                    <div className="w-2 h-2 bg-red-500 rounded-full" />
                  )}
                  
                  {file.status === 'pending' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(index)}
                      className="h-6 w-6 p-0"
                      disabled={isUploading}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
            
            {/* Extract Preview button */}
            <div className="flex justify-end mt-4">
              <Button
                onClick={handleExtractPreview}
                disabled={files.length === 0 || isExtracting || files.every(f => f.status !== 'pending')}
                className="min-w-[120px]"
              >
                {isExtracting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Extracting...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    Extract Preview
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}