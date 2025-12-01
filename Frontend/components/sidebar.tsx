"use client"

import { Plus, MessageSquare, ChevronLeft, ChevronRight, MoreVertical } from "lucide-react"
import { ConversationAPI, ProjectAPI } from "@/lib/api"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import * as DropdownMenu from "@radix-ui/react-dropdown-menu"
import { MoveToProjectDialog } from "@/components/move-to-project-dialog"
import { useState } from "react"

// Local interface for sidebar display (simplified from API Conversation)
interface SidebarConversation {
  id: string;
  title: string;
  timestamp?: string;
  preview?: string;
  project_id?: string;
}

// Simple project type for sidebar (subset of API Project)
interface SidebarProject {
  id: string;
  name: string;
  is_default?: boolean;
}

interface SidebarProps {
  isCollapsed: boolean
  onToggleCollapse: () => void
  onNewConversation: () => void
  currentConversationId?: string
  onSelectConversation: (id: string) => void
  conversations: SidebarConversation[]
  setConversations: React.Dispatch<React.SetStateAction<SidebarConversation[]>> | ((convs: SidebarConversation[]) => void)
  // New props for projects
  projects: SidebarProject[]
  setProjects: React.Dispatch<React.SetStateAction<SidebarProject[]>> | ((projects: SidebarProject[]) => void)
  userId: string
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
    projects,
    setProjects,
    userId,
  } = props;

  const [selectedProjectId, setSelectedProjectId] = useState<string>('ungrouped');

  // Create new project via API
  const handleNewProject = async () => {
    const name = window.prompt('Enter new project name');
    if (!name) return;

    try {
      const result = await ProjectAPI.create({
        user_id: userId,
        name: name.trim(),
      });
      setProjects([...projects, { id: result.project.id, name: result.project.name }]);
    } catch (error) {
      alert('Failed to create project');
      console.error(error);
    }
  };

  // Rename project via API
  const handleRenameProject = async (id: string) => {
    const name = window.prompt('Enter new project name');
    if (!name) return;

    try {
      await ProjectAPI.update(id, userId, { name: name.trim() });
      setProjects(projects.map(p => p.id === id ? { ...p, name: name.trim() } : p));
    } catch (error) {
      alert('Failed to rename project');
      console.error(error);
    }
  };

  // Delete project via API
  const handleDeleteProject = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this project? Conversations will be moved to Ungrouped.')) return;

    try {
      await ProjectAPI.delete(id, userId);
      setProjects(projects.filter(p => p.id !== id));
      // Move conversations to ungrouped locally
      setConversations(conversations.map(c =>
        c.project_id === id ? { ...c, project_id: undefined } : c
      ));
      if (selectedProjectId === id) {
        setSelectedProjectId('ungrouped');
      }
    } catch (error) {
      alert('Failed to delete project');
      console.error(error);
    }
  };

  // 删除会话
  const handleDeleteConversation = async (conversationId: string) => {
    if (!window.confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await ConversationAPI.delete(conversationId, userId);
      // Remove from local state instead of reloading
      setConversations(conversations.filter(c => c.id !== conversationId));
    } catch (e) {
      alert('Failed to delete conversation');
    }
  };

  // 移动会话到项目（美化弹窗/React组件）
  const [moveDialog, setMoveDialog] = useState<{ open: boolean; conversationId?: string }>({ open: false });
  const handleMoveConversation = (conversationId: string) => {
    setMoveDialog({ open: true, conversationId });
  };
  const handleMoveDialogSelect = async (projectId: string, projectName?: string) => {
    if (!moveDialog.conversationId) return;

    console.log('[MoveConversation] conversationId:', moveDialog.conversationId, 'projectId:', projectId);

    try {
      // If creating a new project
      if (projectName) {
        const result = await ProjectAPI.create({
          user_id: userId,
          name: projectName.trim(),
        });
        const newProjectId = result.project.id;
        setProjects([...projects, { id: newProjectId, name: projectName.trim() }]);
        // Move conversation to the new project
        await ConversationAPI.move(moveDialog.conversationId, userId, newProjectId);
        setConversations(
          conversations.map(conv =>
            conv.id === moveDialog.conversationId
              ? { ...conv, project_id: newProjectId }
              : conv
          )
        );
      } else {
        // Move to existing project
        await ConversationAPI.move(moveDialog.conversationId, userId, projectId);
        setConversations(
          conversations.map(conv =>
            conv.id === moveDialog.conversationId
              ? { ...conv, project_id: projectId }
              : conv
          )
        );
      }
    } catch (e) {
      alert('Failed to move conversation');
      console.error(e);
    }
  };

  // 会话重命名弹窗状态
  const [renameDialog, setRenameDialog] = useState<{ open: boolean; conversationId?: string }>({ open: false });
  const handleRenameConversation = (conversationId: string) => {
    setRenameDialog({ open: true, conversationId });
  };
  const handleRenameDialogConfirm = async (newTitle: string) => {
    if (!renameDialog.conversationId) return;
    try {
      await ConversationAPI.update(renameDialog.conversationId, userId, { title: newTitle });
      setConversations(
        conversations.map(conv => {
          const base = {
            ...conv,
            timestamp: conv.timestamp || "",
          };
          return conv.id === renameDialog.conversationId ? { ...base, title: newTitle } : base;
        })
      );
      setRenameDialog({ open: false });
    } catch (e) {
      alert('Failed to rename conversation');
    }
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
          {/* Ungrouped (always first) */}
          <button
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-accent/50 transition-all text-left group",
              selectedProjectId === 'ungrouped' && "bg-[#d2ede3] border border-primary/20"
            )}
            onClick={() => setSelectedProjectId('ungrouped')}
          >
            <div className="h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
              <MessageSquare className="h-4 w-4 text-primary" />
            </div>
            <span className="text-sm font-medium">Ungrouped</span>
          </button>

          {/* User's projects */}
          {projects.filter(p => !p.is_default).map((project) => (
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
              {/* Project dropdown menu */}
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <button
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-70 hover:opacity-100 p-1 rounded-full hover:bg-accent transition-opacity"
                    onClick={e => e.stopPropagation()}
                    aria-label="Project more actions"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </button>
                </DropdownMenu.Trigger>
                <DropdownMenu.Content sideOffset={5} className="z-50 min-w-[120px] rounded-md bg-white shadow-lg border p-1">
                  <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer" onClick={() => handleRenameProject(project.id)}>Rename</DropdownMenu.Item>
                  <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer text-red-600" onClick={() => handleDeleteProject(project.id)}>Delete</DropdownMenu.Item>
                </DropdownMenu.Content>
              </DropdownMenu.Root>
            </div>
          ))}

          {/* New Project button */}
          <button
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-accent/50 text-left text-primary font-medium mt-2"
            onClick={handleNewProject}
          >
            <Plus className="h-4 w-4" /> New Project
          </button>
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
                // 'ungrouped' means show conversations without project_id
                const matches = selectedProjectId === 'ungrouped'
                  ? !c.project_id
                  : c.project_id === selectedProjectId;
                return matches;
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
                      <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer" onClick={() => handleRenameConversation(conversation.id)}>Rename</DropdownMenu.Item>
                      <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer" onClick={() => handleDeleteConversation(conversation.id)}>Delete</DropdownMenu.Item>
                      <DropdownMenu.Item className="px-3 py-2 text-sm hover:bg-accent rounded cursor-pointer" onClick={() => handleMoveConversation(conversation.id)}>Move to Project</DropdownMenu.Item>
                    </DropdownMenu.Content>
                  </DropdownMenu.Root>
                  {/* 移动到项目弹窗 */}
                  <MoveToProjectDialog
                    open={moveDialog.open}
                    projects={projects}
                    onClose={() => setMoveDialog({ open: false })}
                    onSelect={handleMoveDialogSelect}
                  />
                  {/* 会话重命名弹窗 */}
                  {renameDialog.open && renameDialog.conversationId === conversation.id && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
                      <div className="bg-white rounded-lg shadow-lg p-6 min-w-[300px]">
                        <h4 className="text-lg font-semibold mb-4">Rename Conversation</h4>
                        <input
                          type="text"
                          className="border rounded px-3 py-2 w-full mb-4"
                          defaultValue={conversation.title}
                          autoFocus
                          onKeyDown={e => {
                            if (e.key === 'Enter') {
                              const value = (e.target as HTMLInputElement).value.trim();
                              if (value) handleRenameDialogConfirm(value);
                            }
                          }}
                          id="rename-conv-input"
                        />
                        <div className="flex gap-2 justify-end">
                          <button
                            className="px-4 py-2 rounded bg-gray-200 hover:bg-gray-300"
                            onClick={() => setRenameDialog({ open: false })}
                          >Cancel</button>
                          <button
                            className="px-4 py-2 rounded bg-primary text-white hover:bg-primary/90"
                            onClick={() => {
                              const input = document.getElementById('rename-conv-input') as HTMLInputElement;
                              const value = input.value.trim();
                              if (value) handleRenameDialogConfirm(value);
                            }}
                          >Confirm</button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
