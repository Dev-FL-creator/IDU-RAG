"use client"

import { useState, useRef, useEffect } from "react"
import { Panel, PanelGroup, PanelResizeHandle, ImperativePanelHandle } from "react-resizable-panels"
import { Sidebar } from "@/components/sidebar"
import { MessageComponent, type Message } from "@/components/message"
import { ChatInput } from "@/components/chat-input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { CompanyDetailPanel } from "@/components/company-detail-panel"
import { GripVertical, PanelLeftOpen, AlertCircle, Wifi, WifiOff } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Company } from "@/types/company"
import { mockCompanies } from "@/lib/mock-companies"
import { BackendAPI, SearchResult } from "@/lib/api"

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
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')
  const sidebarPanelRef = useRef<ImperativePanelHandle>(null)
  const detailPanelRef = useRef<ImperativePanelHandle>(null)

  // 检查Backend连接状态
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const health = await BackendAPI.healthCheck()
        setBackendStatus(health.ok ? 'connected' : 'disconnected')
      } catch (error) {
        setBackendStatus('disconnected')
      }
    }
    
    checkBackendHealth()
    // 每30秒检查一次连接状态
    const interval = setInterval(checkBackendHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      contents: [{ type: "text", content }],
    }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      // 如果Backend连接正常，使用真实搜索
      if (backendStatus === 'connected') {
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
          resultTexts.push(`我找到了 ${searchResponse.results.length} 个相关的结果：\n`)
          
          searchResponse.results.forEach((result: SearchResult, index: number) => {
            const score = (result.combined_score * 100).toFixed(1)
            let resultText = `${index + 1}. **${result.org_name || '组织'}**`
            
            if (result.country) resultText += ` (${result.country})`
            if (result.industry) resultText += ` - ${result.industry}`
            
            resultText += `\n   评分: ${score}%`
            
            if (result.capabilities && result.capabilities.length > 0) {
              resultText += `\n   能力: ${result.capabilities.slice(0, 3).join(', ')}`
            }
            
            if (result.content) {
              const preview = result.content.substring(0, 200)
              resultText += `\n   内容: ${preview}${result.content.length > 200 ? '...' : ''}`
            }
            
            resultText += '\n'
            resultTexts.push(resultText)

            // 如果有完整的组织信息，创建公司卡片
            if (result.org_name) {
              const company: Company = {
                id: result.id,
                name: result.org_name,
                icon: "/images/avatars/company-default.png",
                shortDescription: result.industry || "研究组织",
                fullDescription: result.content || "",
                industry: result.industry || "",
                founded: "",
                location: result.country || "",
                website: "",
                images: [],
                metrics: [
                  {
                    label: "相关度",
                    value: `${score}%`,
                    trend: "neutral" as const
                  }
                ]
              }
              companies.push(company)
            }
          })
        } else {
          resultTexts.push("抱歉，没有找到相关的结果。请尝试使用不同的关键词。")
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
      } else {
        // Backend未连接时的模拟响应
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          contents: [
            {
              type: "text",
              content: "⚠️ Backend服务未连接。请确保Backend服务器运行在 http://localhost:8000\n\n这是一个模拟响应。要获取真实的搜索结果，请启动Backend服务。",
            },
          ],
        }
        setMessages((prev) => [...prev, aiMessage])
      }
    } catch (error) {
      console.error('搜索失败:', error)
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: "assistant",
        contents: [
          {
            type: "text",
            content: `❌ 搜索失败: ${error instanceof Error ? error.message : '未知错误'}`,
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
                <div className="flex-1">
                  <h1 className="text-xl font-semibold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                    AI Assistant
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    Discover companies, analyze data, and explore detailed insights
                  </p>
                </div>
              </div>
              
              {/* Backend连接状态指示器 */}
              <div className="flex items-center gap-2">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium ${
                        backendStatus === 'connected' 
                          ? 'bg-green-500/10 text-green-600 border border-green-500/20' 
                          : backendStatus === 'disconnected'
                          ? 'bg-red-500/10 text-red-600 border border-red-500/20'
                          : 'bg-yellow-500/10 text-yellow-600 border border-yellow-500/20'
                      }`}>
                        {backendStatus === 'connected' ? (
                          <Wifi className="h-3 w-3" />
                        ) : (
                          <WifiOff className="h-3 w-3" />
                        )}
                        {backendStatus === 'connected' ? 'Backend已连接' : 
                         backendStatus === 'disconnected' ? 'Backend未连接' : '检查中...'}
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      {backendStatus === 'connected' 
                        ? '后端服务运行正常，可以进行实时搜索' 
                        : '后端服务未连接，将使用模拟数据'}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </div>

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
