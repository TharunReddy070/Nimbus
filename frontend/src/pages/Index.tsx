import React, { useState, useEffect } from 'react';
import ChatInput from '@/components/ChatInput';
import ChatMessage from '@/components/ChatMessage';
import CanvasView from '@/components/CanvasView';
import { useChatState } from '@/hooks/useChatState';
import { cn } from '@/lib/utils';

const Index = () => {
  const { 
    state, 
    addMessage, 
    messagesEndRef,
  } = useChatState();
  
  const [hasStarted, setHasStarted] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  useEffect(() => {
    // Consider conversation started if there are any messages
    if (state.messages.length > 0 && !hasStarted) {
      setHasStarted(true);
    }
  }, [state.messages, hasStarted]);

  const handleSendMessage = (message: string) => {
    // Create message with files if any are attached
    addMessage(message, 'user', 'text', state.files.length ? [...state.files] : undefined);
    
    // Always show the same markdown response
  };

  // Add the missing toggle sidebar handler
  const handleToggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className={cn(
      "chat-container",
      state.canvasContent ? "grid grid-cols-2 gap-0" : "block"
    )}>
      <div className="flex flex-col min-h-screen relative">
        {/* Messages section */}
        {hasStarted ? (
          <div className="chat-messages">
            {state.messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            
            {/* Show typing indicator */}
            {state.isTyping && (
              <div className="self-start chat-message">
                <div className="message-bubble bg-chat-bot border border-gray-200">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-300 rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-gray-300 rounded-full animate-pulse delay-75"></div>
                    <div className="w-2 h-2 bg-gray-300 rounded-full animate-pulse delay-150"></div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center flex-grow">
            <div className="text-center max-w-md mx-auto px-4 py-20">
              <h1 className="text-3xl font-semibold mb-4">How can I help you today?</h1>
              <p className="text-gray-500 mb-8">
                Ask me anything, upload files, or request help with code.
              </p>
            </div>
          </div>
        )}

        {/* Input section - positioned differently based on conversation state */}
        <div className={cn(
          hasStarted ? "chat-input-container" : "flex flex-col items-center justify-center max-w-3xl w-full mx-auto px-4 pb-8"
        )}>
          <ChatInput 
            onSendMessage={handleSendMessage}
            autoFocus={true}
          />
        </div>
      </div>

      {/* Canvas view */}
      {state.canvasContent && (
        <CanvasView content={state.canvasContent} />
      )}
    </div>
  );
};

export default Index;
