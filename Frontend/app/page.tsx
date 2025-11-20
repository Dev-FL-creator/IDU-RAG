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
  // 会话列表和当前会话
  const [conversations, setConversations] = useState<{
    id: string
    title: string
    messages: Message[]
    timestamp: string
  }[]>([
    {
      id: "1",
      title: "Image Analysis Discussion",
      messages: mockMessages,
      timestamp: "2 hours ago"
    }
  ])
  const [currentConversationId, setCurrentConversationId] = useState<string>(conversations[0].id)
  const [messages, setMessages] = useState<Message[]>(conversations[0].messages)
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [showDetailPanel, setShowDetailPanel] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [currentView, setCurrentView] = useState<'chat' | 'upload'>('chat')
  const sidebarPanelRef = useRef<ImperativePanelHandle>(null)
  const detailPanelRef = useRef<ImperativePanelHandle>(null)
  // 聊天区滚动ref
  const chatScrollRef = useRef<HTMLDivElement>(null)

  // 发送消息并保存到当前会话
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
            let c = result.content.trim()
            c = c.replace(/:selected:?/gi, '').replace(/\bselected\b/gi, '')
            let displayContent = c.length > 1000 ? c.substring(0, 1000) + '...' : c
            resultText += `\n   Content: ${displayContent}`
          }
          resultText += '\n'
          resultTexts.push(resultText)
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
              searchResult: result,
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
          ...companies.slice(0, 3).map(company => ({
            type: "company" as const,
            content: company.name,
            company: company
          }))
        ],
      }
      setMessages((prev) => {
        const updated = [...prev, aiMessage]
        setConversations((convs) =>
          convs.map(conv =>
            conv.id === currentConversationId ? { ...conv, messages: updated } : conv
          )
        )
        return updated
      })
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
      setMessages((prev) => {
        const updated = [...prev, errorMessage]
        setConversations((convs) =>
          convs.map(conv =>
            conv.id === currentConversationId ? { ...conv, messages: updated } : conv
          )
        )
        return updated
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 新建会话，保存当前会话内容
  const handleNewConversation = () => {
    const now = Date.now()
    setConversations((prev) => {
      const idx = prev.findIndex(conv => conv.id === currentConversationId)
      let updated = [...prev]
      if (idx !== -1) {
        updated[idx] = {
          ...updated[idx],
          messages: messages.map(m => ({
            ...m,
            role: m.role === "assistant" ? "assistant" : "user",
            contents: m.contents.map(c => ({
              ...c,
              type: c.type === "text" ? "text" : c.type === "image" ? "image" : "company"
            }))
          }))
        }
      }
      const newConv = {
        id: now.toString(),
        title: `Conversation ${updated.length + 1}`,
        messages: [
          {
            id: now.toString(),
            role: "assistant" as const,
            contents: [
              {
                type: "text" as const,
                content: "Hello! Starting a new conversation. How can I help you today?",
              },
            ],
          },
        ],
        timestamp: new Date().toLocaleString()
      }
      return [...updated, newConv]
    })
    setCurrentConversationId(now.toString())
    setMessages([
      {
        id: now.toString(),
        role: "assistant",
        contents: [
          {
            type: "text",
            content: "Hello! Starting a new conversation. How can I help you today?",
          },
        ],
      },
    ])
    setSelectedCompany(null)
  }

  // 切换会话
  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id)
    const conv = conversations.find(c => c.id === id)
    setMessages(conv ? conv.messages : [])
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

  // 点击公司卡片后：选中公司 + 自动折叠任务栏
  const handleCompanyClick = (company: Company) => {
    setSelectedCompany(company)
    setIsCollapsed(true)
    // 补充：如果此时 sidebar 还在，主动折叠一下
    sidebarPanelRef.current?.collapse()
  }

  // 公司详情关闭时恢复任务栏
  const handleCloseCompanyDetail = () => {
    setSelectedCompany(null)
    setIsCollapsed(false)
  }

  // PDF上传后自动滚动到底部
  const handleUploadComplete = (results: any) => {
    console.log('Upload completed:', results)
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
    setTimeout(() => {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        contents: [
          {
            type: "text",
            content: "✅ Indexing completed! You can now search and chat with the new data.",
          },
        ],
      }])
      setTimeout(() => {
        chatScrollRef.current?.scrollIntoView({ behavior: 'smooth' })
      }, 100)
    }, 1500)
    setCurrentView('chat')
    setTimeout(() => {
      chatScrollRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, 300)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <PanelGroup direction="horizontal">
        {/* 只有在没有选中公司时才渲染 Sidebar Panel */}
        {!selectedCompany && (
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
            {!isCollapsed && (
              <Sidebar
                isCollapsed={isCollapsed}
                onToggleCollapse={handleToggleSidebar}
                onNewConversation={handleNewConversation}
                currentConversationId={currentConversationId}
                onSelectConversation={handleSelectConversation}
                conversations={conversations}
              />
            )}
          </Panel>
        )}

        {/* 主区：聊天和公司详情分栏，可拖拽 */}
        {selectedCompany ? (
          <>
            {/* 只剩两个 Panel，各 50%，自然对半分 */}
            <Panel defaultSize={50} minSize={20} maxSize={80}>
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
                  {/* View Toggle Buttons */}
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
                          <div ref={chatScrollRef} />
                        </div>
                      </ScrollArea>
                    </div>
                    <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
                  </>
                ) : (
                  <>
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
            <PanelResizeHandle className="w-1 hover:w-2 bg-border hover:bg-primary/50 transition-all relative group">
              <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-6 flex items-center justify-center">
                <GripVertical className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
            </PanelResizeHandle>
            <Panel defaultSize={50} minSize={20} maxSize={80}>
              <CompanyDetailPanel
                company={selectedCompany}
                onClose={handleCloseCompanyDetail}
              />
            </Panel>
          </>
        ) : (
          <Panel defaultSize={80} minSize={30} maxSize={100}>
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
                {/* View Toggle Buttons */}
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
                        <div ref={chatScrollRef} />
                      </div>
                    </ScrollArea>
                  </div>
                  <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
                </>
              ) : (
                <>
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
        )}
      </PanelGroup>
    </div>
  )
}
