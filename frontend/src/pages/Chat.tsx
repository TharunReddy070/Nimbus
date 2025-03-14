import React, { useState, useEffect } from 'react';
import ChatMessage from '@/components/ChatMessage';
import ChatInput from '@/components/ChatInput';
import { useChatState } from '@/hooks/useChatState';
import { cn } from '@/lib/utils';
import { X, ChevronDown, ChevronUp} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import CanvasView from '@/components/CanvasView';

// Processing Steps Handler Component
interface ProcessingStepsHandlerProps {
  steps: Array<{ 
    message: string;
    completed?: boolean;
  }>;
  collapsed?: boolean;
  isStreaming?: boolean;
}

const ProcessingStepsHandler: React.FC<ProcessingStepsHandlerProps> = ({ 
  steps, 
  collapsed: initialCollapsed = false,
  isStreaming = false
}) => {
  const [collapsed, setCollapsed] = useState(initialCollapsed);
  
  // Remove auto-collapse effect during streaming
  useEffect(() => {
    // Only auto-collapse when it's not streaming and we have a final message
    if (!isStreaming && steps.length > 0 && !collapsed) {
      const timer = setTimeout(() => {
        setCollapsed(true);
      }, 800); // Slight delay before collapsing
      
      return () => clearTimeout(timer);
    }
  }, [steps.length, isStreaming]);
  
  // Force expand if we're streaming
  useEffect(() => {
    if (isStreaming && collapsed) {
      setCollapsed(false);
    }
  }, [isStreaming]);
  
  if (!steps || steps.length === 0) {
    return null;
  }
  
  return (
    <div className="mt-3 mb-4 ml-11 max-sm:ml-6">
      <div 
        className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 cursor-pointer mb-1 px-2"
        onClick={() => setCollapsed(!collapsed)}
      >
        <span className="font-medium">{isStreaming ? "Processing..." : "Processing Steps"}</span>
        <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors">
          {collapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </button>
      </div>
      
      {!collapsed && (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-md p-4 transition-all duration-300 relative">
          {/* Vertical connecting line with exact pixel placement */}
          <div 
            className="absolute w-[2px] bg-gray-200 dark:bg-gray-700" 
            style={{
              left: "11px",  // Precise positioning aligned with dot centers
              top: "28px",   // Start after first dot's top edge
              bottom: "28px" // End before last dot's bottom edge
            }}
          >
            {/* Flowing animation for the line */}
            {isStreaming && steps.length > 1 && (
              <div 
                className="absolute top-0 left-0 w-full bg-gradient-to-b from-primary to-primary/20"
                style={{ 
                  height: `${Math.min(100, (steps.length / 5) * 100)}%`,
                  transition: 'height 0.6s cubic-bezier(0.4, 0, 0.2, 1)'
                }}
              />
            )}
          </div>
          
          {steps.map((step, index) => {
            const isLastStep = index === steps.length - 1;
            const isStreamed = isStreaming && isLastStep && !step.completed;
            const isCompleted = step.completed || false;
            
            return (
              <div 
                key={index} 
                className={`mb-5 last:mb-0 flex items-center transition-all duration-300 ${
                  isStreamed ? 'animate-slide-in' : ''
                }`}
              >
                {/* Dot container with forced centering */}
                <div className="relative" style={{ width: "24px", marginRight: "16px" }}>
                  {/* The dot with precise positioning */}
                  <div 
                    className={`w-6 h-6 rounded-full flex items-center justify-center absolute ${
                      isCompleted ? 'bg-green-100 border-2 border-green-400' : 
                      isStreamed ? 'bg-blue-100 border-2 border-blue-400' : 'bg-gray-100 border-2 border-gray-300'
                    }`}
                    style={{ 
                      left: "-10.5px", // Precise manual adjustment to center the dot on the line
                      top: "0px"
                    }}
                  >
                    <div 
                      className={`w-2 h-2 rounded-full ${
                        isCompleted ? 'bg-green-500' : 
                        isStreamed ? 'bg-blue-500 animate-pulse' : 'bg-gray-400'
                      }`}
                    />
                    
                    {/* Ripple effect for streaming dot */}
                    {isStreamed && (
                      <div className="absolute inset-0 rounded-full border-4 border-blue-400 opacity-75 animate-ripple" />
                    )}
                  </div>
                </div>
                
                {/* Step text - perfectly aligned with dot */}
                <div 
                  className={`step-content ${
                    isCompleted ? 'text-green-700 font-medium' : 
                    isStreamed ? 'text-blue-700 font-medium' : 'text-gray-700'
                  }`}
                >
                  <p className="text-[15px] max-sm:text-[11px] leading-relaxed">
                    {step.message}
                    {isCompleted && " ✓"}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const Chat = () => {
  const { 
    state, 
    addMessage, 
    clearCanvas,
    clearMessages,
    messagesEndRef,
    toggleCanvas,
    regenerateMessage
  } = useChatState();
  
  const [hasStarted, setHasStarted] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { toast } = useToast();
  
  useEffect(() => {
    if (state.messages.length > 0 && !hasStarted) {
      setHasStarted(true);
    }
  }, [state.messages, hasStarted]);

  useEffect(() => {
    if (state.canvasContent && sidebarOpen) {
      setSidebarOpen(false);
    }
  }, [state.canvasContent, sidebarOpen]);

  const handleSendMessage = (message: string) => {
    addMessage(message, 'user', 'text', state.files.length ? [...state.files] : undefined);
  };

  const handleClearChat = () => {
    clearMessages();
    setHasStarted(false);
    setSidebarOpen(false);
    toast({
      title: "Chat cleared",
      description: "All messages have been cleared",
    });
  };

  const handleEditMessage = (messageId: string) => {
    if (sidebarOpen) {
      setSidebarOpen(false);
    }
    
    console.log('Edit message:', messageId);
    toast({
      title: "Edit message",
      description: "Message editing functionality will be implemented soon",
    });
  };

  const handleRegenerateResponse = (messageId: string) => {
    regenerateMessage(messageId);
    toast({
      title: "Regenerating response",
      description: "Regenerating the response for your message",
    });
  };

  const renderCitationBadges = (message) => {
    if (!message.hasCitations) return null;
    
    const handleViewCitation = (citation) => {
      const citationContent = `
        <div class="p-4 bg-white rounded-md">
          <h2 class="text-xl font-semibold mb-4">${citation.company_name}</h2>
          <div class="text-gray-700 mb-6">
            ${citation.content}
          </div>
          <div class="mt-4">
            <a href="${citation.link}" target="_blank" rel="noopener noreferrer" class="flex items-center text-blue-600 hover:underline">
              Visit source
            </a>
          </div>
        </div>      `;
      
      toggleCanvas(citationContent);
    };

    return (
      <div className="mt-1 mb-2 ml-11">
        <div className="text-sm font-medium text-gray-600 mb-2">Sources:</div>
        <div className="flex flex-wrap gap-2 pb-4">
          {message.citations && message.citations.map((citation, index) => (
            <button
              key={index}
              onClick={() => handleViewCitation(citation)}
              className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-blue-100 text-blue-800 hover:bg-blue-200 transition-colors border border-blue-200"
            >
              {citation.company_name}
            </button>
          ))}
        </div>
      </div>
    );
  };

  const renderChatItems = () => {
    const items = [];
    const messageMap = new Map();
    let lastUserMessageIndex = -1;
    let lastMessageIsBot = false;
    let hasPendingSteps = state.processingSteps.length > 0;

    state.messages.forEach((message, index) => {
      if (message.sender === 'user') {
        lastUserMessageIndex = items.length;
        lastMessageIsBot = false;
      } else if (message.sender === 'bot') {
        lastMessageIsBot = true;
      }
      
      const messageComponent = (
        <ChatMessage 
          key={`${message.sender}-${message.id}`}
          message={message} 
          onRegenerateResponse={() => handleRegenerateResponse(message.id)}
        />
      );
      
      items.push(messageComponent);
      messageMap.set(message.id, items.length - 1);
      
      if (message.sender === 'bot' && message.hasCitations) {
        items.push(
          <div key={`citations-${message.id}`}>
            {renderCitationBadges(message)}
          </div>
        );
      }
    });
    
    let insertedCount = 0;
    for (let i = 0; i < state.messages.length; i++) {
      const message = state.messages[i];
      
      if (message.sender === 'bot' && message.processingSteps && message.processingSteps.length > 0 && i > 0) {
        let j = i - 1;
        while (j >= 0 && state.messages[j].sender !== 'user') {
          j--;
        }
        
        if (j >= 0) {
          const userMessage = state.messages[j];
          const userPos = messageMap.get(userMessage.id);
          
          if (userPos !== undefined) {
            const insertPos = userPos + 1 + insertedCount;
            
            items.splice(
              insertPos,
              0,
              <ProcessingStepsHandler 
                key={`steps-${message.id}`} 
                steps={message.processingSteps} 
                collapsed={true}
                isStreaming={false}
              />
            );
            
            insertedCount++;
          }
        }
      }
    }

    if (hasPendingSteps && lastUserMessageIndex !== -1 && !lastMessageIsBot) {
      items.splice(
        lastUserMessageIndex + 1 + insertedCount, 
        0, 
        <ProcessingStepsHandler 
          key="current-processing-steps" 
          steps={state.processingSteps} 
          collapsed={false}
          isStreaming={true}
        />
      );
    }

    return items;
  };

  return (
    <div className="chat-container">      
      <div className={cn(
        "flex flex-col min-h-screen relative",
        state.canvasContent ? "lg:w-1/2" : "w-full"
      )}>
        
        {hasStarted ? (
          <div className="chat-messages-container">
            <div className="chat-messages">
              <div className="max-w-3xl mx-auto w-full">
                {renderChatItems().map((item, index) => (
                  <div key={index} className="chat-item-wrapper">
                    {item}
                  </div>
                ))}
                <div ref={messagesEndRef} className="h-4" />
              </div>
            </div>
          </div>
        ) : (
          <div className="chat-welcome">
            <div className="max-w-4xl mx-auto w-full">
              <div className="text-center p-4 sm:p-8 -mt-6 sm:-mt-12">
                <h1 className="text-2xl sm:text-3xl font-bold mb-6 sm:mb-10">Welcome to Nimbus</h1>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-5 mt-4 sm:mt-6">
                  {/* Template 1: AWS Case Studies */}
                  <div 
                    className="cursor-pointer bg-white p-3 sm:p-5 rounded-lg shadow-sm border border-gray-200 hover:border-orange-300 hover:shadow-md transition-all"
                    onClick={() => {
                      const templateQuery = "Show me AWS case studies about machine learning implementation in healthcare companies and summarize the key results they achieved.";
                      handleSendMessage(templateQuery);
                    }}
                  >
                    <div className="flex items-start">
                      <div className="bg-orange-100 p-2 sm:p-3 rounded-full mr-3 sm:mr-4">
                        <svg width="20" height="20" viewBox="0 0 24 24" className="text-orange-600" fill="currentColor">
                          <path d="M9.3 21.5L6.3 4.5H9.8L12.1 19.5H12.3L14.8 4.5H17.7L20.4 19.5H20.6L23.1 4.5H26.5L23.3 21.5H19.8L17.1 7.5H16.9L14.3 21.5H9.3Z M0 17.4H4.8V21H0V17.4Z M0 8.7H4.8V12.3H0V8.7Z M0 0H4.8V3.6H0V0Z M1.2 4.9H3.6V7.3H1.2V4.9Z M1.2 13.7H3.6V16.1H1.2V13.7Z"></path>
                        </svg>
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-base sm:text-lg mb-1">AWS Case Studies</h3>
                        <p className="text-gray-600 text-xs sm:text-sm">Explore 3500+ AWS customer success stories across industries.</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Template 2: GCP Case Studies */}
                  <div 
                    className="cursor-pointer bg-white p-3 sm:p-5 rounded-lg shadow-sm border border-gray-200 hover:border-green-300 hover:shadow-md transition-all"
                    onClick={() => {
                      const templateQuery = "Find Google Cloud Platform case studies related to retail companies that implemented big data analytics. What technology stack did they use and what were the business outcomes?";
                      handleSendMessage(templateQuery);
                    }}
                  >
                    <div className="flex items-start">
                      <div className="bg-green-100 p-2 sm:p-3 rounded-full mr-3 sm:mr-4">
                        <svg width="20" height="20" viewBox="0 0 24 24" className="text-green-600" fill="currentColor">
                          <path d="M12.2 4.5L19.5 8.3V15.9L12.2 19.7L4.8 15.9V8.3L12.2 4.5ZM9.5 10.4V14.2L12.2 15.8L14.9 14.2V10.4L12.2 8.8L9.5 10.4Z"></path>
                        </svg>
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-base sm:text-lg mb-1">GCP Case Studies</h3>
                        <p className="text-gray-600 text-xs sm:text-sm">Access 500+ Google Cloud case studies with implementation details.</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Template 3: Interesting Questions */}
                  <div 
                    className="cursor-pointer bg-white p-3 sm:p-5 rounded-lg shadow-sm border border-gray-200 hover:border-purple-300 hover:shadow-md transition-all"
                    onClick={() => {
                      const templateQuery = "What are the most innovative uses of AWS and GCP in the healthcare sector? Can you provide examples of successful implementations?";
                      handleSendMessage(templateQuery);
                    }}
                  >
                    <div className="flex items-start">
                      <div className="bg-purple-100 p-2 sm:p-3 rounded-full mr-3 sm:mr-4">
                        <svg width="20" height="20" viewBox="0 0 24 24" className="text-purple-600" fill="currentColor">
                          <path d="M12 4L3 9L12 14L21 9L12 4Z" />
                          <path d="M20 11L12 16L4 11V16L12 21L20 16V11Z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-base sm:text-lg mb-1">Innovative Use Cases</h3>
                        <p className="text-gray-600 text-xs sm:text-sm">Discover groundbreaking cloud implementations.</p>
                      </div>
                    </div>
                  </div>

                  {/* Template 4: AWS for Startups */}
                  <div 
                    className="cursor-pointer bg-white p-3 sm:p-5 rounded-lg shadow-sm border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all"
                    onClick={() => {
                      const templateQuery = "What are the best practices for using AWS for startups? Can you provide examples of successful implementations?";
                      handleSendMessage(templateQuery);
                    }}
                  >
                    <div className="flex items-start">
                      <div className="bg-blue-100 p-2 sm:p-3 rounded-full mr-3 sm:mr-4">
                        <svg width="20" height="20" viewBox="0 0 24 24" className="text-blue-600" fill="currentColor">
                          <path d="M11.3,3.1c3.8-2.2,8.7-0.7,10.9,3.2c0.9,1.5,1.3,3.3,1.3,5c0,0.7-0.1,1.4-0.2,2.1h-7.1c-0.2,0-0.3,0.1-0.3,0.2c0,0,0,0,0,0v11.3c0,0.2,0.1,0.3,0.3,0.4c0,0,0,0,0,0H5.9c-0.2,0-0.3-0.1-0.3-0.3c0,0,0,0,0,0V8.6c0-0.2,0.1-0.3,0.3-0.3c0,0,0,0,0,0h5.1C11.2,8.2,11.3,8.1,11.3,8c0,0,0,0,0,0V3.1z"></path>
                        </svg>
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-base sm:text-lg mb-1">AWS for Startups</h3>
                        <p className="text-gray-600 text-xs sm:text-sm">Learn how AWS supports startups with cost-effective solutions.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className={cn(
          "chat-input-container",
          state.canvasContent ? "lg:w-1/2 lg:pr-0" : "w-full"
        )}>
          <ChatInput 
            onSendMessage={handleSendMessage}
            onClearChat={handleClearChat}
            autoFocus={true}
            isCentered={!hasStarted}
          />
        </div>
      </div>

      {state.canvasContent && (
        <div className="canvas-view fixed top-0 right-0 w-full lg:w-1/2 h-full bg-white border-l border-gray-200 overflow-auto z-30 lg:z-auto">
          <div className="canvas-header sticky top-0 z-10 flex justify-between items-center p-3 sm:p-4 bg-white border-b border-gray-200">
            <h2 className="canvas-title text-base sm:text-lg font-semibold"></h2>
            <button 
              onClick={clearCanvas}
              className="canvas-close hover:bg-gray-100 p-1.5 sm:p-2 rounded-full transition-colors"
              aria-label="Close canvas"
              title="Close canvas"
            >
              <X className="h-4 w-4 sm:h-5 sm:w-5" />
            </button>
          </div>
          <CanvasView content={state.canvasContent} />
        </div>
      )}
    </div>
  );
};

export default Chat;

