
import React from 'react';
import { siteConfig } from '@/config/content';
import { XCircle } from 'lucide-react';

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onClearChat: () => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({ isOpen, onClose, onClearChat }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 left-0 w-64 bg-sidebar text-sidebar-foreground shadow-lg z-20 animate-slide-right">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="p-4 border-b border-sidebar-border flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-md bg-sidebar-primary flex items-center justify-center text-sidebar-primary-foreground font-bold">
              N
            </div>
            <span className="font-semibold">{siteConfig.name}</span>
          </div>
          <button 
            onClick={onClose}
            className="p-1 rounded-full hover:bg-sidebar-accent text-sidebar-foreground/70 hover:text-sidebar-foreground transition-colors"
          >
            <XCircle className="h-5 w-5" />
          </button>
        </div>

        {/* Sidebar content */}
        <div className="flex-1 p-4 overflow-y-auto">
          {/* You can add history, favorited prompts, etc. here */}
        </div>

        {/* Footer with clear chat button */}
        <div className="p-4 border-t border-sidebar-border">
          <button 
            onClick={onClearChat}
            className="w-full py-2 rounded-md bg-sidebar-accent hover:bg-sidebar-accent/80 text-sidebar-accent-foreground transition-colors"
          >
            Clear Chat
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatSidebar;
