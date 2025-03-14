import React from 'react';
import { Copy, RotateCcw } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface ChatMessageActionsProps {
  messageId: string;
  sender: string;
  content: string;
  onRegenerate?: () => void;
}

const ChatMessageActions: React.FC<ChatMessageActionsProps> = ({
  messageId,
  sender,
  content,
  onRegenerate
}) => {
  const isUser = sender === 'user';
  const { toast } = useToast();
  
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(content);
      toast({
        title: "Copied to clipboard",
        description: "Message content has been copied to your clipboard",
      });
    } catch (error) {
      console.error('Failed to copy:', error);
      toast({
        title: "Failed to copy",
        description: "Could not copy the message to clipboard",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="message-actions">
      {/* Copy button */}
      <button 
        className="message-action-button"
        aria-label="Copy message"
        title="Copy message"
        onClick={copyToClipboard}
      >
        <Copy className="h-3.5 w-3.5" />
      </button>
      
      {/* Regenerate button - only for user messages */}
      {isUser && onRegenerate && (
        <button 
          className="message-action-button"
          aria-label="Regenerate response"
          title="Regenerate response"
          onClick={onRegenerate}
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
};

export default ChatMessageActions;
