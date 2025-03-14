import React, { useState } from 'react';
import { Search, FileText, Image, Send, Menu, Sparkles, Trash2 } from 'lucide-react';

// Import Shadcn UI Dialog and Tooltip components
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { Button } from "@/components/ui/button";

interface ToolbarProps {
  onSubmit: () => void;
  onClearChat?: () => void;
  disabled?: boolean;
}

const Toolbar: React.FC<ToolbarProps> = ({ 
  onSubmit, 
  onClearChat,
  disabled 
}) => {
  // Create refs for file inputs
  const imageInputRef = React.useRef<HTMLInputElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  
  // State for dialog
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);

  const handleImageClick = () => {
    imageInputRef.current?.click();
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleClearClick = () => {
    if (onClearChat) {
      // Open confirmation dialog instead of using window.confirm
      setConfirmDialogOpen(true);
    }
  };

  const handleConfirmClear = () => {
    if (onClearChat) {
      onClearChat();
      setConfirmDialogOpen(false);
    }
  };

  return (
    <div className="chat-toolbar">
      <div className="flex items-center space-x-1">
        {onClearChat && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button 
                  className="chat-toolbar-button text-red-500 hover:bg-red-50"
                  aria-label="Clear conversation"
                  onClick={handleClearClick}
                >
                  <Trash2 className="h-5 w-5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p>Clear the conversation</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
      
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button 
              className="chat-send-button"
              aria-label="Send message"
              onClick={onSubmit}
              disabled={disabled}
            >
              <Send className="h-5 w-5 mr-1" />
              <span>Send</span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p>Submit your message</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Confirmation Dialog */}
      <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Clear Conversation</DialogTitle>
            <DialogDescription>
              Are you sure you want to clear the conversation? This will delete all messages.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex space-x-2 justify-end pt-4">
            <Button variant="outline" onClick={() => setConfirmDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleConfirmClear}>
              Yes, Clear
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Toolbar;
