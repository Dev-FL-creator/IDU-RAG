"use client"

import { useState, useRef, useEffect } from "react"
import { Panel, PanelGroup, PanelResizeHandle, ImperativePanelHandle } from "react-resizable-panels"
import { Sidebar } from "@/components/sidebar"
import { MessageComponent, type Message } from "@/components/message"
import { ChatInput } from "@/components/chat-input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { CompanyDetailPanel } from "@/components/company-detail-panel"
import { GripVertical, PanelLeftOpen, AlertCircle } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Company } from "@/types/company"
import { mockCompanies } from "@/lib/mock-companies"
import { BackendAPI, SearchResult } from "@/lib/api"
import { PDFUpload } from "@/components/pdf-upload"

const mockMessages: Message[] = [
  {
    id: "1",
    role: "assistant",
    contents: [
      {
        type: "text",
        content: "Hello! I'm your AI assistant. I can help you discover companies, analyze data, and provide detailed insights. Would you like to see some companies in the renewable energy sector?",
      },
    ],
  },
  {
    id: "2",
    role: "user",
    contents: [
      {
        type: "text",
        content: "Yes, show me companies in renewable energy and AI.",
      },
    ],
  },
  {
    id: "3",
    role: "assistant",
    contents: [
      {
        type: "text",
        content: "Here are some innovative companies you might be interested in:",
      },
      {
        type: "company",
        content: mockCompanies[0].name,
        company: mockCompanies[0],
      },
      {
        type: "company",
        content: mockCompanies[1].name,
        company: mockCompanies[1],
      },
      {
        type: "company",
        content: mockCompanies[2].name,
        company: mockCompanies[2],
      },
      {
        type: "text",
        content: "Click on any company card to see more details, including their latest projects, metrics, and image gallery.",
      },
    ],
  },
]

export default function Home() {
  const [messages, setMessages] = useState<Message[]>(mockMessages)
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [currentConversationId, setCurrentConversationId] = useState<string>("1")
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [showDetailPanel, setShowDetailPanel] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [currentView, setCurrentView] = useState<'chat' | 'upload'>('chat')
  const sidebarPanelRef = useRef<ImperativePanelHandle>(null)
  const detailPanelRef = useRef<ImperativePanelHandle>(null)



  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      contents: [{ type: "text", content }],
    }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      const searchResponse = await BackendAPI.hybridSearch({
        query: content,
        alpha: 0.7,
        kvec: 10,
        kbm25: 10,
        top_n: 5
      })

      // 将搜索结果转换为消息
      const resultTexts: string[] = []
      const companies: Company[] = []

      if (searchResponse.results.length > 0) {
        resultTexts.push(`Found ${searchResponse.results.length} relevant results:\n`)
        
        searchResponse.results.forEach((result: SearchResult, index: number) => {
          const score = (result.combined_score * 100).toFixed(1)
          let resultText = `${index + 1}. **${result.org_name || 'Organization'}**`
          
          if (result.country) resultText += ` (${result.country})`
          if (result.industry) resultText += ` - ${result.industry}`
          
          resultText += `\n   Score: ${score}%`
          
          if (result.capabilities && result.capabilities.length > 0) {
            resultText += `\n   Capabilities: ${result.capabilities.slice(0, 3).join(', ')}`
          }
          
          if (result.content) {
            // 智能内容摘要：优先显示关键信息
            const content = result.content.trim()
            let preview = ""
            
            // 尝试提取关键句子（包含公司名称、技术、服务等）
            const keywordPatterns = [
              /.*?(?:company|corporation|technology|research|development|service|product|solution).*?[.!?]/gi,
              /.*?(?:specialized|focus|expert|leader|pioneer).*?[.!?]/gi,
              /.*?(?:über uns|about|contact|solution|service).*?[.!?]/gi
            ]
            
            for (const pattern of keywordPatterns) {
              const matches = content.match(pattern)
              if (matches && matches.length > 0) {
                preview = matches[0].substring(0, 150).trim()
                break
              }
            }
            
            // 如果没有找到关键句子，使用前150个字符，但确保在句子边界截断
            if (!preview) {
              preview = content.substring(0, 150)
              const lastSentence = preview.lastIndexOf('.')
              const lastExclamation = preview.lastIndexOf('!')
              const lastQuestion = preview.lastIndexOf('?')
              const lastPunct = Math.max(lastSentence, lastExclamation, lastQuestion)
              
              if (lastPunct > 50) { // 确保有足够的内容
                preview = preview.substring(0, lastPunct + 1)
              }
            }
            
            resultText += `\n   Content: ${preview}${content.length > preview.length ? '...' : ''}`
          }
          
          resultText += '\n'
          resultTexts.push(resultText)

          // 如果有完整的组织信息，创建公司卡片
          if (result.org_name) {
            const company: Company = {
              id: result.id,
              name: result.org_name,
              icon: "/images/avatars/company-default.png",
              shortDescription: result.industry || "Research Organization",
              fullDescription: result.content || "",
              industry: result.industry || "",
              founded: result.founded_year || "",
              location: result.country || "",
              website: result.website || "",
              images: [],
              searchResult: result, // 包含完整的搜索结果数据
              metrics: [
                {
                  label: "Relevance",
                  value: `${score}%`,
                  trend: "neutral" as const
                }
              ]
            }
            companies.push(company)
          }
        })
      } else {
        resultTexts.push("Sorry, no relevant results found. Please try using different keywords.")
      }

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        contents: [
          {
            type: "text",
            content: resultTexts.join('\n')
          },
          // 添加公司卡片
          ...companies.slice(0, 3).map(company => ({
            type: "company" as const,
            content: company.name,
            company: company
          }))
        ],
      }
      setMessages((prev) => [...prev, aiMessage])
    } catch (error) {
      console.error('Search failed:', error)
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: "assistant",
        contents: [
          {
            type: "text",
            content: `❌ Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
        ],
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewConversation = () => {
    setMessages([
      {
        id: Date.now().toString(),
        role: "assistant",
        contents: [
          {
            type: "text",
            content: "Hello! Starting a new conversation. How can I help you today?",
          },
        ],
      },
    ])
    setCurrentConversationId(Date.now().toString())
    setSelectedCompany(null)
  }

  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id)
    setMessages(mockMessages)
    setSelectedCompany(null)
  }

  const handleToggleSidebar = () => {
    const panel = sidebarPanelRef.current
    if (panel) {
      if (isCollapsed) {
        panel.expand()
      } else {
        panel.collapse()
      }
    }
  }

  const handleCompanyClick = (company: Company) => {
    setSelectedCompany(company)
  }

  const handleCloseCompanyDetail = () => {
    setSelectedCompany(null)
  }

  const handleUploadComplete = (results: any) => {
    console.log('Upload completed:', results)
    // 添加成功消息到聊天
    const successMessage: Message = {
      id: Date.now().toString(),
      role: "assistant",
      contents: [
        {
          type: "text",
          content: `✅ PDF upload completed successfully! ${results.message || 'Files have been processed and indexed.'}`,
        },
      ],
    }
    setMessages((prev) => [...prev, successMessage])
    // 切换回聊天视图
    setCurrentView('chat')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <PanelGroup direction="horizontal">
        {/* Sidebar Panel */}
        <Panel
          ref={sidebarPanelRef}
          defaultSize={20}
          minSize={5}
          maxSize={35}
          collapsible={true}
          collapsedSize={5}
          onCollapse={() => setIsCollapsed(true)}
          onExpand={() => setIsCollapsed(false)}
        >
          <Sidebar
            isCollapsed={isCollapsed}
            onToggleCollapse={handleToggleSidebar}
            onNewConversation={handleNewConversation}
            currentConversationId={currentConversationId}
            onSelectConversation={handleSelectConversation}
          />
        </Panel>

        {/* Resize Handle */}
        {!isCollapsed && (
          <PanelResizeHandle className="w-1 hover:w-2 bg-border hover:bg-primary/50 transition-all relative group">
            <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-6 flex items-center justify-center">
              <GripVertical className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
          </PanelResizeHandle>
        )}

        {/* Chat Panel */}
        <Panel defaultSize={selectedCompany ? 45 : 80} minSize={30}>
          <div className="flex flex-col h-full">
            {/* Chat Header */}
            <div className="border-b bg-gradient-to-r from-background to-muted/20 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                {isCollapsed && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={handleToggleSidebar}
                          className="h-9 w-9 shrink-0"
                        >
                          <PanelLeftOpen className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Open sidebar</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
                <div>
                  <h1 className="text-xl font-semibold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                    {currentView === 'chat' ? 'AI Assistant' : 'PDF Upload'}
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    {currentView === 'chat' 
                      ? 'Discover companies, analyze data, and explore detailed insights'
                      : 'Upload PDF documents to expand the knowledge base'
                    }
                  </p>
                </div>
              </div>
              
              {/* View Toggle Buttons - Now in the right side */}
              <div className="flex items-center gap-2">
                <Button
                  variant={currentView === 'chat' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setCurrentView('chat')}
                  className="h-8"
                >
                  Chat
                </Button>
                <Button
                  variant={currentView === 'upload' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setCurrentView('upload')}
                  className="h-8"
                >
                  Upload PDF
                </Button>
              </div>
            </div>

            {/* Content Area */}
            {currentView === 'chat' ? (
              <>
                {/* Messages Area */}
                <div className="flex-1 overflow-hidden">
                  <ScrollArea className="h-full">
                    <div className="max-w-5xl mx-auto p-6 space-y-1">
                      {messages.map((message) => (
                        <MessageComponent
                          key={message.id}
                          message={message}
                          onCompanyClick={handleCompanyClick}
                        />
                      ))}
                    </div>
                  </ScrollArea>
                </div>

                {/* Input Area */}
                <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
              </>
            ) : (
              <>
                {/* PDF Upload Area */}
                <div className="flex-1 overflow-hidden">
                  <ScrollArea className="h-full">
                    <div className="max-w-4xl mx-auto p-6">
                      <PDFUpload 
                        onUploadComplete={handleUploadComplete}
                      />
                    </div>
                  </ScrollArea>
                </div>
              </>
            )}
          </div>
        </Panel>

        {/* Company Detail Panel */}
        {selectedCompany && (
          <>
            <PanelResizeHandle className="w-1 hover:w-2 bg-border hover:bg-primary/50 transition-all relative group">
              <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-6 flex items-center justify-center">
                <GripVertical className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
            </PanelResizeHandle>
            <Panel defaultSize={35} minSize={25} maxSize={50}>
              <CompanyDetailPanel
                company={selectedCompany}
                onClose={handleCloseCompanyDetail}
              />
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  )
}
