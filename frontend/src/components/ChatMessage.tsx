import React from 'react';
import { Message } from '@/hooks/useChatState';
import { cn } from '@/lib/utils';
import ChatMessageActions from './chat/ChatMessageActions';
import ReactMarkdown from 'react-markdown';
import { Clock, User, Bot } from 'lucide-react';

interface ChatMessageProps {
  message: Message;
  onRegenerateResponse?: (messageId: string) => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  onRegenerateResponse
}) => {
  const isUser = message.sender === 'user';
  
  // Format content based on type
  const renderContent = () => {
    if (message.type === 'code' || message.type === 'markdown' || message.type === 'canvas') {
      return (
        <div className="prose prose-slate dark:prose-invert max-w-full">
          <ReactMarkdown
            components={{
              code: (props) => {
                const { className, children, ...rest } = props;
                const match = /language-(\w+)/.exec(className || '');
                
                // Check if it's an inline code block using a different approach
                if (className?.includes('inline') || !className) {
                  return <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm" {...rest}>{children}</code>;
                }
                
                return (
                  <pre className="bg-gray-800 text-gray-100 p-3 rounded-md my-2 overflow-x-auto">
                    <code className={match ? `language-${match[1]}` : ''} {...rest}>{children}</code>
                  </pre>
                );
              },
              p({ children }) {
                return <p className="mb-4">{children}</p>;
              },
              h1({ children }) {
                return <h1 className="text-2xl font-bold mb-4 mt-6">{children}</h1>;
              },
              h2({ children }) {
                return <h2 className="text-xl font-semibold mb-3 mt-5">{children}</h2>;
              },
              ul({ children }) {
                return <ul className="list-disc pl-6 mb-4">{children}</ul>;
              },
              ol({ children }) {
                return <ol className="list-decimal pl-6 mb-4">{children}</ol>;
              },
              a({ href, children }) {
                return <a href={href} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>;
              }
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      );
    }
    
    // For regular text messages
    return <span className="whitespace-pre-wrap">{message.content}</span>;
  };

  return (
    <div className="chat-message group">
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1 max-sm:hidden">
          {isUser ? (
            <User className="h-5 w-5 text-primary" />
          ) : (
            <Bot className="h-5 w-5 text-primary" />
          )}
        </div>
        
        {/* Message content */}
        <div 
          className={cn(
            "message-bubble flex-1",
            isUser ? "user-message" : "ai-message",
          )}
        >
          {/* Message content only, no image handling */}
          {renderContent()}
        </div>
      </div>

      {/* Message metadata and actions */}
      <div className="message-meta ml-11">
        <div className="flex items-center">
          <Clock className="h-3 w-3 mr-1" />
          <span>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        
        <ChatMessageActions 
          messageId={message.id}
          sender={message.sender}
          content={message.content}
          onRegenerate={onRegenerateResponse ? () => onRegenerateResponse(message.id) : undefined}
        />
      </div>

      {/* Display files if any */}
      {message.files && message.files.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2 ml-11">
          {message.files.map(file => (
            <div key={file.id} className="file-preview-item group">
              {file.type.startsWith('image/') ? (
                <img src={file.url} alt={file.name} className="file-preview-image" />
              ) : (
                <div className="file-preview-document">
                  <span>{file.name}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatMessage;
