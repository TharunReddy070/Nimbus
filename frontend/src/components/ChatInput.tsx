import React, { useState, useRef, useEffect } from 'react';
import Toolbar from './Toolbar';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onClearChat?: () => void;
  disabled?: boolean;
  autoFocus?: boolean;
  isCentered?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onClearChat,
  disabled = false,
  autoFocus = false,
  isCentered = false,
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  const handleSubmit = () => {
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
      
      // Restore textarea to original height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  return (
    <div className={cn(
      "chat-input-wrapper", 
      isCentered ? "shadow-md" : "",
      "transition-all duration-300 hover:shadow-lg"
    )}>
      
      {/* Text input */}
      <div className="px-3 py-2">
        <textarea
          ref={textareaRef}
          className="w-full resize-none outline-none placeholder:text-gray-500 text-gray-800 min-h-[50px] max-h-[600px] overflow-y-auto" // Adjusted minimum height
          placeholder="Type a message..."
          value={message}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          rows={1} // Reduced the default rows for initial height
          style={{ height: 'auto' }} // Ensure the height is auto-resized
          disabled={disabled}
        />
      </div>
      <Toolbar 
        onSubmit={handleSubmit}
        onClearChat={onClearChat}
        disabled={disabled || (!message.trim())}
      />
    </div>
  );
};

export default ChatInput;
