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
  status: 'pending' | 'extracting' | 'success' | 'error'
  error?: string
  textLength?: number
}

export function PDFUpload({ onUploadComplete, disabled }: PDFUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([])

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
    const allExtractedData: any[] = []
    
    try {
      // 逐个处理文件
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i]
        const fileName = file.name
        
        // 更新当前文件状态为extracting
        setFiles(prev => prev.map(f => 
          f.name === fileName 
            ? { ...f, status: 'extracting' as const }
            : f
        ))

        try {
          // 创建只包含当前文件的FileList
          const singleFileList = new DataTransfer()
          singleFileList.items.add(file)
          
          const response = await BackendAPI.extractPDFPreview(singleFileList.files)
          
          if (response.extracted_data && response.extracted_data.length > 0) {
            const extractResult = response.extracted_data[0]
            allExtractedData.push(extractResult)
            
            if (extractResult.error) {
              // 更新文件状态为error
              setFiles(prev => prev.map(f => 
                f.name === fileName 
                  ? { ...f, status: 'error' as const, error: extractResult.error }
                  : f
              ))
            } else {
              // 更新文件状态为success
              setFiles(prev => prev.map(f => 
                f.name === fileName 
                  ? { ...f, status: 'success' as const, textLength: extractResult.text_length }
                  : f
              ))
            }
          } else {
            // 没有返回数据
            setFiles(prev => prev.map(f => 
              f.name === fileName 
                ? { ...f, status: 'error' as const, error: 'No data returned' }
                : f
            ))
          }
          
        } catch (fileError) {
          console.error(`Extraction failed for ${fileName}:`, fileError)
          setFiles(prev => prev.map(f => 
            f.name === fileName 
              ? { 
                  ...f, 
                  status: 'error' as const,
                  error: fileError instanceof Error ? fileError.message : 'Extraction failed'
                }
              : f
          ))
        }
        
        // 添加小延迟，让用户看到进度
        if (i < selectedFiles.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 100))
        }
      }
      
      // 设置所有成功提取的数据
      setExtractedData(allExtractedData.filter(data => !data.error))
      
    } catch (error) {
      console.error('Extraction process failed:', error)
      // 如果整个过程失败，将剩余pending状态的文件标记为error
      setFiles(prev => prev.map(f => 
        f.status === 'extracting' || f.status === 'pending'
          ? { 
              ...f, 
              status: 'error' as const,
              error: error instanceof Error ? error.message : 'Extraction process failed'
            }
          : f
      ))
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
          onClick={() => !disabled && !isExtracting && fileInputRef.current?.click()}
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
            disabled={disabled || isExtracting}
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
                    {file.textLength && ` • ${file.textLength} characters extracted`}
                    {file.status === 'extracting' && ' • Extracting...'}
                    {file.error && ` • Error: ${file.error}`}
                  </div>
                </div>
                
                {/* Status indicator */}
                <div className="flex items-center gap-2">
                  {file.status === 'extracting' && (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                      <span className="text-xs text-blue-600">Extracting</span>
                    </>
                  )}
                  {file.status === 'success' && (
                    <>
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      <span className="text-xs text-green-600">Ready</span>
                    </>
                  )}
                  {file.status === 'error' && (
                    <>
                      <div className="w-2 h-2 bg-red-500 rounded-full" />
                      <span className="text-xs text-red-600">Failed</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setFiles(prev => prev.map(f => 
                          f.name === file.name ? { ...f, status: 'pending' as const, error: undefined } : f
                        ))}
                        className="h-6 w-6 p-0 ml-1"
                        disabled={isExtracting}
                        title="Retry extraction"
                      >
                        <Upload className="h-3 w-3" />
                      </Button>
                    </>
                  )}
                  
                  {file.status === 'pending' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(index)}
                      className="h-6 w-6 p-0"
                      disabled={isExtracting}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
            
            {/* File status summary */}
            {files.length > 0 && (
              <div className="flex items-center justify-between mt-4 text-xs text-muted-foreground">
                <div>
                  {files.length} files • 
                  {files.filter(f => f.status === 'success').length} ready • 
                  {files.filter(f => f.status === 'extracting').length} extracting • 
                  {files.filter(f => f.status === 'error').length} failed
                </div>
                {isExtracting && (
                  <div className="text-blue-600">
                    Processing {files.filter(f => f.status === 'extracting').length > 0 ? 
                      files.findIndex(f => f.status === 'extracting') + 1 : 
                      files.filter(f => f.status !== 'pending').length + 1
                    } of {files.length}
                  </div>
                )}
              </div>
            )}
            
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