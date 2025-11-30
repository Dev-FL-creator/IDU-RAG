"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { Panel, PanelGroup, PanelResizeHandle, ImperativePanelHandle } from "react-resizable-panels"
import { Sidebar } from "@/components/sidebar"
import { MessageComponent, type Message } from "@/components/message"
import { ChatInput } from "@/components/chat-input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { CompanyDetailPanel } from "@/components/company-detail-panel"
import { GripVertical, PanelLeftOpen, LogIn, LogOut, User as UserIcon } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Company } from "@/types/company"
import { BackendAPI, SearchResult, User, ConversationAPI, ProjectAPI, Conversation, Message as ApiMessage } from "@/lib/api"
import { PDFUpload } from "@/components/pdf-upload"
import { AuthModal } from "@/components/auth-modal"

export default function Home() {
  // ==========================================================================
  // Auth State
  // ==========================================================================
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authLoading, setAuthLoading] = useState(true)

  // ==========================================================================
  // Conversations & Projects State
  // ==========================================================================
  const [conversations, setConversations] = useState<{
    id: string
    title: string
    timestamp?: string
    preview?: string
    project_id?: string
  }[]>([])

  const [projects, setProjects] = useState<{
    id: string
    name: string
    is_default?: boolean
  }[]>([])

  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])

  // Load user data (conversations and projects)
  const loadUserData = useCallback(async (userId: string) => {
    console.log('[loadUserData] Loading data for user:', userId)
    try {
      // Load conversations
      const conversationsResult = await ConversationAPI.list(userId)
      console.log('[loadUserData] Loaded conversations:', conversationsResult)
      if (conversationsResult.conversations && conversationsResult.conversations.length > 0) {
        const convs = conversationsResult.conversations.map((conv: Conversation) => ({
          id: conv.id,
          title: conv.title || 'Untitled',
          timestamp: conv.updated_at || '',
          preview: conv.last_message_preview || '',
          project_id: conv.project_id,
        }))
        console.log('[loadUserData] Mapped conversations with project_ids:', convs.map((c) => ({ id: c.id, title: c.title, project_id: c.project_id })))
        setConversations(convs)
        const latestId = convs[0].id
        setCurrentConversationId(latestId)
      }

      // Load projects
      const projectsResult = await ProjectAPI.list(userId)
      console.log('[loadUserData] Loaded projects:', projectsResult)
      if (projectsResult.projects) {
        const mappedProjects = projectsResult.projects.map(p => ({
          id: p.id,
          name: p.name,
          is_default: p.is_default
        }))
        console.log('[loadUserData] Mapped projects:', mappedProjects)
        setProjects(mappedProjects)
      }
    } catch (error) {
      console.error('[loadUserData] Failed to load user data:', error)
    }
  }, [])

  // Check for existing login on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('user')
    if (savedUser) {
      try {
        const user = JSON.parse(savedUser)
        setCurrentUser(user)
        // Load user's data on page refresh
        loadUserData(user.id)
      } catch {
        localStorage.removeItem('user')
        localStorage.removeItem('user_id')
      }
    }
    setAuthLoading(false)
  }, [loadUserData])

  const handleLoginSuccess = (user: User) => {
    setCurrentUser(user)
    // Load user's conversations and projects
    loadUserData(user.id)
  }

  const handleLogout = () => {
    setCurrentUser(null)
    localStorage.removeItem('user')
    localStorage.removeItem('user_id')
    // Clear user-specific data
    setConversations([])
    setProjects([])
    setCurrentConversationId(null)
    setMessages([])
  }

  // Load conversation messages when conversation changes
  useEffect(() => {
    if (currentConversationId && currentUser) {
      ConversationAPI.get(currentConversationId, currentUser.id)
        .then((result) => {
          if (result.messages && result.messages.length > 0) {
            const loaded = result.messages.map((msg: ApiMessage, idx: number) => ({
              id: msg.id || String(idx),
              role: msg.role as 'assistant' | 'user',
              contents: [{ type: 'text' as const, content: msg.content }],
            }))
            setMessages(loaded)
          } else {
            setMessages([])
          }
        })
        .catch(() => {
          setMessages([])
        })
    }
  }, [currentConversationId, currentUser])

  // ==========================================================================
  // UI State
  // ==========================================================================
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [currentView, setCurrentView] = useState<'chat' | 'upload'>('chat')
  const sidebarPanelRef = useRef<ImperativePanelHandle>(null)
  const chatScrollRef = useRef<HTMLDivElement>(null)

  // ==========================================================================
  // Message Handling
  // ==========================================================================
  const handleSendMessage = async (content: string) => {
    const userId = currentUser?.id || 'anonymous'

    // Save user message (only if logged in and has conversation)
    if (currentUser && currentConversationId) {
      ConversationAPI.addMessage(currentConversationId, {
        user_id: userId,
        role: 'user',
        content,
      }).catch(err => console.error('Failed to save user message:', err))
    }

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

        // Save AI message (only if logged in and has conversation)
        if (currentUser && currentConversationId) {
          ConversationAPI.addMessage(currentConversationId, {
            user_id: userId,
            role: 'assistant',
            content: resultTexts.join('\n'),
          }).catch(err => console.error('Failed to save AI message:', err))

          // Auto-generate title for new conversations
          const convIdx = conversations.findIndex(c => c.id === currentConversationId)
          if (convIdx !== -1 && (conversations[convIdx].title === 'Untitled' || conversations[convIdx].title.startsWith('Conversation'))) {
            const conversationText = `User: ${content}\nAI: ${resultTexts.join('\n')}`
            ConversationAPI.generateTitle(conversationText)
              .then((title) => {
                ConversationAPI.update(currentConversationId, currentUser.id, { title }).then(() => {
                  setConversations(prev => prev.map((c, i) => i === convIdx ? { ...c, title } : c))
                })
              })
              .catch(() => {})
          }
        }
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
            content: `Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
        ],
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  // ==========================================================================
  // Conversation Management
  // ==========================================================================
  const handleNewConversation = async () => {
    if (!currentUser) return

    try {
      // Create conversation in backend first
      const result = await ConversationAPI.create({
        user_id: currentUser.id,
        title: `Conversation ${conversations.length + 1}`,
      })

      const newConvId = result.conversation.id
      const newConv = {
        id: newConvId,
        title: result.conversation.title,
        timestamp: new Date().toLocaleString(),
      }
      setConversations((prev) => [...prev, newConv])
      setCurrentConversationId(newConvId)

      const welcomeMsg: Message = {
        id: newConvId,
        role: "assistant",
        contents: [
          {
            type: "text",
            content: "Hello! Starting a new conversation. How can I help you today?",
          },
        ],
      }
      setMessages([welcomeMsg])

      // Save welcome message to backend
      await ConversationAPI.addMessage(newConvId, {
        user_id: currentUser.id,
        role: 'assistant',
        content: "Hello! Starting a new conversation. How can I help you today?",
      })
      setSelectedCompany(null)
    } catch (error) {
      console.error('Failed to create conversation:', error)
      alert('Failed to create conversation')
    }
  }

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

  const handleCompanyClick = (company: Company) => {
    setSelectedCompany(company)
    setIsCollapsed(true)
    sidebarPanelRef.current?.collapse()
  }

  const handleCloseCompanyDetail = () => {
    setSelectedCompany(null)
    setIsCollapsed(false)
  }

  const handleUploadComplete = (results: any) => {
    console.log('Upload completed:', results)
    const successMessage: Message = {
      id: Date.now().toString(),
      role: "assistant",
      contents: [
        {
          type: "text",
          content: `PDF upload completed successfully! ${results.message || 'Files have been processed and indexed.'}`,
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
            content: "Indexing completed! You can now search and chat with the new data.",
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

  // ==========================================================================
  // Header Component (with auth buttons)
  // ==========================================================================
  const Header = ({ showSidebarToggle = false }: { showSidebarToggle?: boolean }) => (
    <div className="border-b bg-gradient-to-r from-background to-muted/20 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        {showSidebarToggle && isCollapsed && (
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

      {/* Right side: View toggle + Auth */}
      <div className="flex items-center gap-4">
        {/* View Toggle */}
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

        {/* Auth Section */}
        <div className="flex items-center gap-2 pl-4 border-l">
          {authLoading ? (
            <div className="h-8 w-20 bg-muted animate-pulse rounded" />
          ) : currentUser ? (
            <>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-full">
                      <UserIcon className="h-4 w-4" />
                      <span className="text-sm font-medium max-w-[100px] truncate">
                        {currentUser.username || currentUser.email.split('@')[0]}
                      </span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>{currentUser.email}</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="h-8 gap-1"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </Button>
            </>
          ) : (
            <Button
              variant="default"
              size="sm"
              onClick={() => setShowAuthModal(true)}
              className="h-8 gap-1"
            >
              <LogIn className="h-4 w-4" />
              Sign In
            </Button>
          )}
        </div>
      </div>
    </div>
  )

  // ==========================================================================
  // Chat Content Component
  // ==========================================================================
  const ChatContent = () => (
    <>
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="max-w-5xl mx-auto p-6 space-y-1">
            {messages.length === 0 && (
              <div className="text-center text-muted-foreground py-20">
                <p className="text-lg mb-2">Welcome to AI Assistant</p>
                <p className="text-sm">
                  {currentUser
                    ? "Start a conversation by typing a message below."
                    : "Sign in to save your conversations and organize them into projects."
                  }
                </p>
              </div>
            )}
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
  )

  // ==========================================================================
  // Render
  // ==========================================================================
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <PanelGroup direction="horizontal">
        {/* Sidebar - Only show for logged-in users and when no company is selected */}
        {currentUser && !selectedCompany && (
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
                setConversations={setConversations}
                projects={projects}
                setProjects={setProjects}
                userId={currentUser.id}
              />
            )}
          </Panel>
        )}

        {/* Main Content */}
        {selectedCompany ? (
          <>
            <Panel defaultSize={50} minSize={20} maxSize={80}>
              <div className="flex flex-col h-full">
                <Header showSidebarToggle={!!currentUser} />
                {currentView === 'chat' ? <ChatContent /> : (
                  <div className="flex-1 overflow-hidden">
                    <ScrollArea className="h-full">
                      <div className="max-w-4xl mx-auto p-6">
                        <PDFUpload onUploadComplete={handleUploadComplete} />
                      </div>
                    </ScrollArea>
                  </div>
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
          <Panel defaultSize={currentUser ? 80 : 100} minSize={30} maxSize={100}>
            <div className="flex flex-col h-full">
              <Header showSidebarToggle={!!currentUser} />
              {currentView === 'chat' ? <ChatContent /> : (
                <div className="flex-1 overflow-hidden">
                  <ScrollArea className="h-full">
                    <div className="max-w-4xl mx-auto p-6">
                      <PDFUpload onUploadComplete={handleUploadComplete} />
                    </div>
                  </ScrollArea>
                </div>
              )}
            </div>
          </Panel>
        )}
      </PanelGroup>

      {/* Auth Modal */}
      <AuthModal
        open={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onLoginSuccess={handleLoginSuccess}
      />
    </div>
  )
}
