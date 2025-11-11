"use client"

import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Card } from "@/components/ui/card"
import { Bot, User } from "lucide-react"
import { ImageViewer } from "@/components/image-viewer"
import { CompanyCard } from "@/components/company-card"
import { Company } from "@/types/company"

export interface MessageContent {
  type: "text" | "image" | "company"
  content: string
  alt?: string
  company?: Company
}

export interface Message {
  id: string
  role: "user" | "assistant"
  contents: MessageContent[]
}

interface MessageProps {
  message: Message
  onCompanyClick?: (company: Company) => void
}

export function MessageComponent({ message, onCompanyClick }: MessageProps) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex gap-4 mb-6 group", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <Avatar className={cn("h-8 w-8 mt-1", isUser ? "bg-primary" : "bg-gradient-to-br from-purple-500 to-blue-500")}>
        <AvatarFallback className={cn(isUser ? "bg-primary text-primary-foreground" : "bg-gradient-to-br from-purple-500 to-blue-500 text-white")}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>

      {/* Message Content */}
      <div className={cn("flex-1 space-y-2", isUser && "flex flex-col items-end")}>
        <div className="text-xs font-semibold text-muted-foreground mb-1">
          {isUser ? "You" : "Assistant"}
        </div>

        <div className={cn("space-y-3 max-w-[85%]", isUser && "items-end")}>
          {message.contents.map((content, index) => (
            <div key={index}>
              {content.type === "text" ? (
                <Card className={cn(
                  "p-4 shadow-sm",
                  isUser
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-card hover:shadow-md transition-shadow"
                )}>
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">
                    {content.content}
                  </div>
                </Card>
              ) : content.type === "image" ? (
                <Card className="p-3 overflow-hidden shadow-sm hover:shadow-md transition-shadow max-w-md">
                  <ImageViewer
                    src={content.content}
                    alt={content.alt || "Message image"}
                  />
                  {content.alt && (
                    <p className="text-xs text-muted-foreground mt-2">
                      {content.alt}
                    </p>
                  )}
                </Card>
              ) : content.type === "company" && content.company ? (
                <CompanyCard
                  company={content.company}
                  onClick={() => onCompanyClick?.(content.company!)}
                  className="max-w-lg"
                />
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
