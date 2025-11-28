"use client"

import { Plus, MessageSquare, ChevronLeft, ChevronRight, MoreVertical } from "lucide-react"
import { ChatAPI } from "@/lib/api"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import * as DropdownMenu from "@radix-ui/react-dropdown-menu"

interface Project {
  id: string
  name: string
}

interface Conversation {
  id: string;
  title: string;
  timestamp?: string;
  preview?: string;
  project_id?: string;
}

// Project列表和当前选中Project由前端状态管理
import { useState } from "react"

interface ProjectWithConvs extends Project {
  conversations: string[] // conversation id 列表
}

// mockConversations 移除，使用props.conversations

interface SidebarProps {
  isCollapsed: boolean
  onToggleCollapse: () => void
  onNewConversation: () => void
  currentConversationId?: string
  onSelectConversation: (id: string) => void
  conversations: Conversation[]
  setConversations: (convs: {
    id: string;
    title: string;
    timestamp: string;
    preview?: string;
    project_id?: string;
  }[]) => void
}

export function Sidebar(props: SidebarProps) {
  const {
    isCollapsed,
    onToggleCollapse,
    onNewConversation,
    currentConversationId,
    onSelectConversation,
    conversations,
    setConversations,
  } = props;

  // 前端Project状态（只存id和name，不存conversations）
  const [projects, setProjects] = useState<Project[]>([
    { id: 'default', name: 'Ungrouped' },
    { id: '1', name: 'Project 1' },
    { id: '2', name: 'Project 2' },
  ]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('default');

  // 新建Project
  const handleNewProject = () => {
    const name = window.prompt('Enter new project name');
    if (!name) return;
    const newId = Date.now().toString();
    setProjects(prev => [...prev, { id: newId, name, conversations: [] }]);
  };

  // Project重命名
  const handleRenameProject = (id: string) => {
    const name = window.prompt('Enter new project name');
    if (!name) return;
    setProjects(prev => prev.map(p => p.id === id ? { ...p, name } : p));
  };

  // Project删除
  const handleDeleteProject = (id: string) => {
    if (!window.confirm('Are you sure you want to delete this project?')) return;
    setProjects(prev => prev.filter(p => p.id !== id));
    // Optionally: move conversations to Ungrouped
  };

  // 删除会话
  const handleDeleteConversation = async (conversationId: string) => {
    if (!window.confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await ChatAPI.deleteConversation(conversationId);
      if (typeof window !== 'undefined') window.location.reload();
    } catch (e) {
      alert('Failed to delete conversation');
    }
  };

  // 移动会话到项目（下拉选择或新建）
  const handleMoveConversation = async (conversationId: string) => {
    let projectId = '';
    let projectName = '';
    // 弹窗选择
    const select = document.createElement('select');
    select.style.width = '100%';
    select.style.margin = '8px 0';
    projects.forEach(p => {
      if (p.id !== 'default') {
        const option = document.createElement('option');
        option.value = p.id;
        option.text = p.name;
        select.appendChild(option);
      }
    });
    const newOpt = document.createElement('option');
    newOpt.value = '__new__';
    newOpt.text = '+ Create New Project';
    select.appendChild(newOpt);

    const wrapper = document.createElement('div');
    wrapper.appendChild(document.createTextNode('Select target project:'));
    wrapper.appendChild(select);
    const input = document.createElement('input');
    input.style.display = 'none';
    input.style.width = '100%';
    input.placeholder = 'Enter new project name';
    wrapper.appendChild(input);

    select.addEventListener('change', () => {
      if (select.value === '__new__') {
        input.style.display = '';
      } else {
        input.style.display = 'none';
      }
    });

    // 用原生dialog实现同步弹窗
    const dialog = document.createElement('dialog');
    dialog.appendChild(wrapper);
    const okBtn = document.createElement('button');
    okBtn.textContent = 'OK';
    okBtn.style.margin = '8px 8px 0 0';
    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.type = 'button';
    dialog.appendChild(okBtn);
    dialog.appendChild(cancelBtn);
    document.body.appendChild(dialog);

    return new Promise<void>((resolve) => {
      okBtn.onclick = async () => {
        if (select.value === '__new__') {
          if (!input.value) {
            input.focus();
            return;
          }
          // 新建项目
          projectId = Date.now().toString();
          projectName = input.value;
          setProjects(prev => [...prev, { id: projectId, name: projectName }]);
        } else {
          projectId = select.value;
        }
        dialog.close();
        document.body.removeChild(dialog);
        try {
          await ChatAPI.moveConversationToProject(conversationId, projectId);
          // 自动刷新会话列表
          if (typeof window !== 'undefined') {
            const userId = localStorage.getItem('user_id');
            if (userId) {
              const history = await ChatAPI.fetchChatHistory(userId);
              if (history && history.length > 0) {
                const convs = history.map((conv: any) => ({
                  id: conv.conversation_id,
                  title: conv.title || 'Untitled',
                  timestamp: conv.timestamp || '',
                  preview: conv.last_message || '',
                  project_id: conv.project_id || undefined,
                }))
                setConversations(convs);
              }
            }
          }
        } catch (e) {
          alert('Failed to move conversation');
        }
        resolve();
      };
      cancelBtn.onclick = () => {
        dialog.close();
        document.body.removeChild(dialog);
        resolve();
      };
    dialog.showModal();
    });
  };
  if (isCollapsed) {
    return (
      <div className="flex flex-col h-full w-16 border-r bg-muted/10">
        <TooltipProvider>
          <div className="p-2 flex flex-col gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onToggleCollapse}
                  className="w-full"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Expand sidebar</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="default"
                  size="icon"
                  onClick={onNewConversation}
                  className="w-full"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">New conversation</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full w-full border-r bg-[#eaf3ee]">
      {/* Header */}
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Conversations
          </h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleCollapse}
            className="h-8 w-8"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>
        <Button
          onClick={onNewConversation}
          className="w-full gap-2 bg-primary hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          New Conversation
        </Button>
      </div>

      <Separator />

      {/* Projects Section */}
      <div className="p-4">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
          Projects
        </h3>
        <div className="space-y-1">
          <button
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-accent/50 text-left text-primary font-medium"
            onClick={handleNewProject}
          >
            <Plus className="h-4 w-4" /> New Project
          </button>
          {projects.map((project) => (
            <div key={project.id} className="relative group">
              <button
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-accent/50 transition-all text-left group",
                  selectedProjectId === project.id && "bg-[#d2ede3] border border-primary/20"
                )}
                onClick={() => setSelectedProjectId(project.id)}
              >
                <div className="h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                  <MessageSquare className="h-4 w-4 text-primary" />
                </div>
                <span className="text-sm font-medium">{project.name}</span>
              </button>
              {/* Project 三个点菜单 */}
              {project.id !== 'default' && (
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button
                      className="absolute top-2 right-2 opacity-70 hover:opacity-100 p-1 rounded-full hover:bg-accent transition-opacity"
                      onClick={e => e.stopPropagation()}
                      aria-label="Project more actions"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Content sideOffset={5} className="z-50 min-w-[120px] rounded-md bg-white shadow-lg border p-1">
                    <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer" onClick={() => handleRenameProject(project.id)}>Rename</DropdownMenu.Item>
                    <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer" onClick={() => handleDeleteProject(project.id)}>Delete</DropdownMenu.Item>
                  </DropdownMenu.Content>
                </DropdownMenu.Root>
              )}
            </div>
          ))}
        </div>
      </div>

      <Separator />

      {/* Conversation History（按Project分组过滤） */}
      <div className="flex-1 overflow-hidden">
        <div className="p-4 pb-2">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {projects.find(p => p.id === selectedProjectId)?.name || 'Conversations'}
          </h3>
        </div>
        <ScrollArea className="h-[calc(100%-2rem)]">
          <div className="px-2 pb-4 space-y-1">
            {[...conversations]
              .filter(c => {
                if (selectedProjectId === 'default') return !c.project_id;
                return c.project_id === selectedProjectId;
              })
              .reverse()
              .map((conversation) => (
                <div key={conversation.id} className="relative group">
                  <button
                    onClick={() => onSelectConversation(conversation.id)}
                    className={cn(
                      "w-full text-left px-3 py-3 rounded-lg transition-all hover:bg-accent/50 flex items-start gap-2 pr-10",
                      currentConversationId === conversation.id &&
                        "bg-[#d2ede3] border border-primary/20"
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <h4 className="text-sm font-medium line-clamp-1">
                          {conversation.title}
                        </h4>
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {conversation.timestamp}
                        </span>
                      </div>
                      {conversation.preview && (
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {conversation.preview}
                        </p>
                      )}
                    </div>
                  </button>
                  {/* 三个点更多操作按钮 */}
                  <DropdownMenu.Root>
                    <DropdownMenu.Trigger asChild>
                      <button
                        className="absolute top-3 right-3 opacity-70 hover:opacity-100 p-1 rounded-full hover:bg-accent transition-opacity"
                        onClick={e => e.stopPropagation()}
                        aria-label="More actions"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Content sideOffset={5} className="z-50 min-w-[140px] rounded-md bg-white shadow-lg border p-1">
                      <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer">Rename</DropdownMenu.Item>
                      <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer" onClick={() => handleDeleteConversation(conversation.id)}>Delete</DropdownMenu.Item>
                      <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer" onClick={() => handleMoveConversation(conversation.id)}>Move to Project</DropdownMenu.Item>
                    </DropdownMenu.Content>
                  </DropdownMenu.Root>
                </div>
              ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
