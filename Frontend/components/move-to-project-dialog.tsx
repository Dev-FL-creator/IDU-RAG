import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface Project {
  id: string;
  name: string;
}

interface MoveToProjectDialogProps {
  open: boolean;
  projects: Project[];
  onClose: () => void;
  onSelect: (projectId: string, projectName?: string) => void;
}

export function MoveToProjectDialog({ open, projects, onClose, onSelect }: MoveToProjectDialogProps) {
  const [selected, setSelected] = useState<string>(projects[0]?.id || "");
  const [newProject, setNewProject] = useState("");
  const isNew = selected === "__new__";

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Move Conversation to Project</DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          <label className="block text-sm font-medium mb-1">Select target project:</label>
          <select
            className="w-full border rounded px-2 py-1"
            value={selected}
            onChange={e => setSelected(e.target.value)}
          >
            {projects.filter(p => p.id !== 'default').map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
            <option value="__new__">+ Create New Project</option>
          </select>
          {isNew && (
            <input
              className="w-full border rounded px-2 py-1 mt-2"
              placeholder="Enter new project name"
              value={newProject}
              onChange={e => setNewProject(e.target.value)}
              autoFocus
            />
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => {
              if (isNew && !newProject) return;
              if (isNew) {
                onSelect(Date.now().toString(), newProject);
              } else {
                onSelect(selected);
              }
              onClose();
            }}
            disabled={isNew && !newProject}
          >
            OK
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
