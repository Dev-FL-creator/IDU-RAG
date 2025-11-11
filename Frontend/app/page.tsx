"use client"

import { useState, useRef } from "react"
import { Panel, PanelGroup, PanelResizeHandle, ImperativePanelHandle } from "react-resizable-panels"
import { Sidebar } from "@/components/sidebar"
import { MessageComponent, type Message } from "@/components/message"
import { ChatInput } from "@/components/chat-input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { CompanyDetailPanel } from "@/components/company-detail-panel"
import { GripVertical, PanelLeftOpen } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Company } from "@/types/company"
import { mockCompanies } from "@/lib/mock-companies"

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
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [currentConversationId, setCurrentConversationId] = useState("1")
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const sidebarPanelRef = useRef<ImperativePanelHandle>(null)

  const handleSendMessage = (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      contents: [{ type: "text", content }],
    }
    setMessages((prev) => [...prev, userMessage])

    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        contents: [
          {
            type: "text",
            content: "This is a simulated response. In a real application, this would be connected to an LLM API that can return company data from your backend.",
          },
          {
            type: "text",
            content: "The system supports multi-part messages with text, images, and interactive company cards!",
          },
        ],
      }
      setMessages((prev) => [...prev, aiMessage])
    }, 800)
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
            <div className="border-b bg-gradient-to-r from-background to-muted/20 backdrop-blur-sm px-6 py-4 flex items-center gap-4">
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
            <ChatInput onSendMessage={handleSendMessage} />
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
