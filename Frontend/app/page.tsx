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
import { BackendAPI, SearchResult, ChatAPI, ChatMessage } from "@/lib/api"
// 假设有用户ID（实际项目可用登录用户ID或本地生成）
const USER_ID = typeof window !== 'undefined' && localStorage.getItem('user_id') || (() => {
  const id = 'user_' + Math.random().toString(36).slice(2, 10)
  if (typeof window !== 'undefined') localStorage.setItem('user_id', id)
  return id
})()
import { PDFUpload } from "@/components/pdf-upload"

// mockMessages 移除，实际数据从后端获取

export default function Home() {
  // 会话列表
  const [conversations, setConversations] = useState<{
    id: string
    title: string
    timestamp: string
    preview?: string
  }[]>([])
  // 当前会话ID
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  // 当前消息
  const [messages, setMessages] = useState<Message[]>([])

  // 首次加载会话列表并自动加载最新会话
  useEffect(() => {
    ChatAPI.fetchChatHistory(USER_ID)
      .then((history) => {
        if (history && history.length > 0) {
          const convs = history.map((conv: any) => ({
            id: conv.conversation_id,
            title: conv.title || 'Untitled',
            timestamp: conv.timestamp || '',
            preview: conv.last_message || '',
          }))
          setConversations(convs)
          // 默认选中最新会话
          const latestId = convs[0].id
          setCurrentConversationId(latestId)
        }
      })
      .catch(() => {})
  }, [])

  // 加载当前会话消息
  useEffect(() => {
    if (currentConversationId) {
      ChatAPI.fetchConversationMessages(currentConversationId)
        .then((msgs) => {
          if (msgs && msgs.length > 0) {
            const loaded = msgs.map((msg: any, idx: number) => ({
              id: (msg.timestamp ? msg.timestamp : String(idx)) + '-' + (msg._id ? msg._id : Math.random().toString(36).slice(2, 8)),
              role: msg.role as 'assistant' | 'user',
              contents: [{ type: 'text' as const, content: msg.content }],
            }))
            setMessages(loaded)
          }
          // 如果没有消息，不清空，保留当前 messages
        })
        .catch(() => {/* 不清空 messages */})
    }
  }, [currentConversationId])
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
    // 保存用户消息到MongoDB，带上当前会话ID
    const userMsg: ChatMessage = {
      user_id: USER_ID,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      conversation_id: currentConversationId || undefined,
    }
    ChatAPI.saveChatMessage(userMsg)
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
        // 保存AI消息到MongoDB，带上当前会话ID
        const aiMsg: ChatMessage = {
          user_id: USER_ID,
          role: 'assistant',
          content: resultTexts.join('\n'),
          timestamp: new Date().toISOString(),
          conversation_id: currentConversationId || undefined,
        }
        ChatAPI.saveChatMessage(aiMsg)
        // 不再更新 conversations 的 messages 字段
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
        // 不再更新 conversations 的 messages 字段
        return updated
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 新建会话，保存当前会话内容
  const handleNewConversation = () => {
    // 生成唯一会话ID
    const newConvId = Date.now().toString();
    // 新会话对象
    const newConv = {
      id: newConvId,
      title: `Conversation ${conversations.length + 1}`,
      timestamp: new Date().toLocaleString(),
    };
    setConversations((prev) => [...prev, newConv]);
    setCurrentConversationId(newConvId);
    // 初始化欢迎消息
    const welcomeMsg: Message = {
      id: newConvId,
      role: "assistant",
      contents: [
        {
          type: "text",
          content: "Hello! Starting a new conversation. How can I help you today?",
        },
      ],
    };
    setMessages([welcomeMsg]);
    // 保存到后端
    const welcomeChatMsg = {
      user_id: USER_ID,
      role: 'assistant',
      content: "Hello! Starting a new conversation. How can I help you today?",
      timestamp: new Date().toISOString(),
      conversation_id: newConvId,
    };
    ChatAPI.saveChatMessage(welcomeChatMsg);
    setSelectedCompany(null);
  }

  // 切换会话
  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id)
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
                currentConversationId={currentConversationId || undefined}
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
