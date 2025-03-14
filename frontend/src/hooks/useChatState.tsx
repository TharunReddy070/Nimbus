import { useState, useEffect, useRef } from 'react';

// Define our message types
export type MessageType = 'text' | 'code' | 'markdown' | 'canvas' | 'image';

export interface FileObject {
  id: string;
  name: string;
  type: string;
  url: string;
}

export interface ProcessingStep {
  message: string;
  collapsed?: boolean;
  completed?: boolean;
}

export interface Citation {
  company_name: string;
  content: string;
  link: string;
}

export interface Message {
  id: string;
  sender: 'user' | 'bot';
  timestamp: number;
  content: string;
  type: MessageType;
  files?: FileObject[];
  hasCode?: boolean;
  hasCitations?: boolean;
  processingSteps?: ProcessingStep[];
  citations?: Citation[];
}

export interface ChatState {
  messages: Message[];
  isTyping: boolean;
  files: FileObject[];
  canvasContent: string | null;
  currentSession?: string;
  processingSteps: ProcessingStep[];
}

// API configuration
const API_BASE_URL = import.meta.env.VITE_RUNNING_ON_LOCAL === 'true'
  ? import.meta.env.VITE_LOCAL_BACKEND_URL
  : import.meta.env.VITE_BACKEND_URL || 'https://nimbus-50656497197.us-central1.run.app';

// Generate unique IDs for messages and files
const generateId = () => Math.random().toString(36).substring(2, 10);

// Local storage keys
const CHAT_STORAGE_KEY = 'chatwise_messages';
const SESSION_ID_KEY = 'chatwise_session_id';

export const useChatState = (showInitialMessages = false) => {
  // Load messages from localStorage if available
  const getInitialState = (): ChatState => {
    try {
      const storedMessages = localStorage.getItem(CHAT_STORAGE_KEY);
      const sessionId = localStorage.getItem(SESSION_ID_KEY);
      
      if (storedMessages) {
        const parsedMessages = JSON.parse(storedMessages);
        return {
          messages: parsedMessages,
          isTyping: false,
          files: [],
          canvasContent: null,
          currentSession: sessionId || undefined,
          processingSteps: [],
        };
      }
    } catch (error) {
      console.error('Error loading chat from localStorage:', error);
    }
    
    return {
      messages: showInitialMessages ? [] : [],
      isTyping: false,
      files: [],
      canvasContent: null,
      processingSteps: [],
    };
  };

  const [state, setState] = useState<ChatState>(getInitialState);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(state.messages));
      if (state.currentSession) {
        localStorage.setItem(SESSION_ID_KEY, state.currentSession);
      }
    } catch (error) {
      console.error('Error saving chat to localStorage:', error);
    }
  }, [state.messages, state.currentSession]);

  // Flag to prevent duplicate requests
  const processingRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Automatically scroll to the bottom whenever messages change or processing steps change
  useEffect(() => {
    scrollToBottom();
  }, [state.messages, state.processingSteps]);

  // Toggle canvas view with different content
  const toggleCanvas = (content: string) => {
    setState(prev => ({
      ...prev,
      canvasContent: content,
    }));
  };

  // Process a chat message 
  const processChat = async (query: string) => {
    // Prevent duplicate requests
    if (processingRef.current) {
      console.log("Already processing a request, skipping");
      return;
    }
    
    processingRef.current = true;
    
    try {
      console.log("processChat called with query:", query);
      
      // Start typing indicator and clear any previous processing steps
      setState(prev => ({ 
        ...prev, 
        isTyping: true,
        processingSteps: []
      }));
      
      try {
        console.log("Making API call to", `${API_BASE_URL}/query`);
        
        // Prepare request body with or without session_id based on if we have one
        const requestBody: Record<string, string> = { user_query: query };
        
        // Add session_id if we have one from previous responses
        if (state.currentSession) {
          requestBody.session_id = state.currentSession;
        }
        
        // Create a fetch request to the streaming API
        const response = await fetch(`${API_BASE_URL}/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        });
        
        if (!response.ok) {
          console.error(`API request failed with status ${response.status}`);
          throw new Error(`API request failed with status ${response.status}`);
        }
        
        if (!response.body) {
          throw new Error("Response body is null");
        }
        
        // Setup a reader to read the stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        let isComplete = false;
        let responseData: any = null;
        const collectedSteps: ProcessingStep[] = [];
        let buffer = ''; // Buffer to handle incomplete JSON chunks
        
        // Process the stream
        while (!isComplete) {
          const { done, value } = await reader.read();
          
          if (done) {
            console.log("Stream complete");
            break;
          }
          
          // Decode the chunk of data
          const chunk = decoder.decode(value, { stream: true });
          console.log("Received chunk:", chunk);
          
          // Process each line in the chunk
          // We need to handle potential incomplete JSON chunks
          // First, prepend any buffered content from previous chunks
          let currentBuffer = buffer || '';
          const lines = chunk.split('\n');
          
          // If we have buffered content, prepend it to the first line
          if (currentBuffer.length > 0) {
            if (lines.length > 0) {
              lines[0] = currentBuffer + lines[0];
              console.log("Combined buffer with new chunk:", lines[0]);
            } else {
              // If we somehow got an empty chunk, keep the buffer
              lines.push(currentBuffer);
            }
            // Reset the buffer now that we've used it
            currentBuffer = '';
          }
          
          for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();
            if (line === '') continue;
            
            // Check for common JSON formatting issues before parsing
            // Sometimes the stream might include non-JSON text or partial content
            const sanitizeLine = (rawLine: string): string => {
              // If the line doesn't start with '{', it might be corrupted or incomplete
              if (!rawLine.startsWith('{')) {
                console.warn("Line doesn't start with '{', attempting to find valid JSON:", rawLine);
                const jsonStart = rawLine.indexOf('{');
                if (jsonStart > -1) {
                  // Extract from the first '{' to the end
                  return rawLine.substring(jsonStart);
                }
              }
              return rawLine;
            };
            
            // Sanitize the line before parsing
            line = sanitizeLine(line);
            
            // Try to parse the current line
            try {
              const data = JSON.parse(line);
              console.log("Parsed data:", data);
              
              if (data.type === "processing_step") {
                // Add the processing step
                console.log("Processing step:", data.message);
                const step = { message: data.message, collapsed: false }; // Make sure steps are not collapsed
                collectedSteps.push(step);
                
                // Update global processing steps that are shown while streaming
                setState(prev => ({
                  ...prev,
                  processingSteps: [...prev.processingSteps, step]
                }));
                
                // Scroll to bottom to show new processing step
                scrollToBottom();
              } else if (data.type === "complete") {
                // Store the final response data
                console.log("Complete response received");
                responseData = data;
                isComplete = true;
                
                // Save the session ID if present in the response
                if (data.session_id && !state.currentSession) {
                  setState(prev => ({
                    ...prev,
                    currentSession: data.session_id
                  }));
                }
              }
            } catch (error) {
              // If this is the last line in the chunk, it might be incomplete
              // So we store it in the buffer to combine with the next chunk
              if (i === lines.length - 1) {
                currentBuffer = line;
                console.log("Storing incomplete JSON in buffer:", currentBuffer);
              } else {
                // If it's not the last line, it's a genuine parsing error
                console.error("Error parsing stream data:", error);
                console.error("Problematic line:", line);
                console.error("Line length:", line.length);
                
                // Try to identify the problematic character position
                if (error instanceof SyntaxError && error.message.includes('column')) {
                  const match = error.message.match(/column (\d+)/i);
                  if (match && match[1]) {
                    const columnPos = parseInt(match[1], 10);
                    const startPos = Math.max(0, columnPos - 20);
                    const endPos = Math.min(line.length, columnPos + 20);
                    console.error(`Context around error (position ${columnPos}):", "${line.substring(startPos, endPos)}"`); 
                    
                    // Advanced JSON recovery attempts
                    try {
                      let fixedLine = line;
                      let fixApplied = false;
                      
                      // For unterminated strings, try to add the closing quote
                      if (error.message.includes('unterminated string')) {
                        fixedLine = line + '"';
                        fixApplied = true;
                      }
                      // For unexpected character errors, try to remove the problematic character
                      else if (error.message.includes('unexpected character')) {
                        // If we know the position, remove the character and surrounding context
                        if (columnPos > 0 && columnPos < line.length) {
                          // Remove a small window around the problematic character
                          fixedLine = line.substring(0, Math.max(0, columnPos - 1)) + 
                                     line.substring(Math.min(line.length, columnPos + 1));
                          fixApplied = true;
                        }
                      }
                      
                      // If we applied a fix, try parsing again
                      if (fixApplied) {
                        console.log("Attempting to fix JSON with modified line:", fixedLine);
                        const data = JSON.parse(fixedLine);
                        console.log("Successfully fixed JSON:", data);
                        
                        // Process the fixed data
                        if (data.type === "processing_step" || data.type === "complete") {
                          // Handle the data as normal by reprocessing with the fix
                          lines[i] = fixedLine; // Replace the line with the fixed version
                          i--; // Reprocess this line with the fix
                          continue;
                        }
                      }
                    } catch (fixError) {
                      // Fixing attempt failed, continue with normal error handling
                      console.error("Attempted to fix JSON but failed:", fixError);
                    }
                  }
                }
              }
            }
          }
          
          // Update the outer buffer with our current buffer
          buffer = currentBuffer;
        }
        
        // When streaming is complete, clear the typing indicator
        // but maintain the collected steps for attaching to the message
        setState(prev => ({ 
          ...prev, 
          isTyping: false,
        }));
        
        if (responseData) {
          const hasCitations = responseData.citation_array && responseData.citation_array.length > 0;
          
          // Mark the final step as "completed" for visual indication
          if (collectedSteps.length > 0) {
            const finalStep = collectedSteps[collectedSteps.length - 1];
            finalStep.completed = true; // Add a completed flag for styling
            
            // Update the global processing steps to show the completed state
            setState(prev => ({
              ...prev,
              processingSteps: [...prev.processingSteps.slice(0, -1), { ...finalStep }]
            }));
            
            // Scroll to bottom to show completed step
            scrollToBottom();
          }
          
          // Allow a brief moment for the user to see the final processing steps before clearing
          setTimeout(() => {
            // Clear the global processing steps as they'll be moved to the message
            setState(prev => ({
              ...prev,
              processingSteps: []
            }));
            
            // Then add the final response as a message with the collected processing steps attached
            console.log("Displaying final response from API");
            addMessage(
              responseData.response, 
              'bot', 
              'markdown', 
              undefined, 
              hasCitations,
              collectedSteps,  // Attach the processing steps to the message
              hasCitations ? responseData.citation_array : undefined
            );
          }, 800); // Small delay for visual transition
        } else {
          throw new Error("No complete response received from API");
        }
      } catch (error) {
        console.error('API call failed:', error);
        throw error; // Re-throw to be caught by the outer catch block
      }
    } catch (error) {
      console.error('Error processing chat:', error);
      
      // Stop typing indicator and clear processing steps
      setState(prev => ({ 
        ...prev, 
        isTyping: false, 
        processingSteps: [] 
      }));
      
      // Create a more detailed error message for the user
      let errorMessage = "Sorry, there was an error processing your request. Please try again.";
      
      // Add more context based on the specific error type
      if (error instanceof SyntaxError && error.message.includes('JSON')) {
        console.error('JSON parsing error details:', error.message);
        // Log more details to help with debugging
        if (error.message.includes('unterminated string')) {
          console.error('Unterminated string error detected - this often happens with large responses');
        } else if (error.message.includes('unexpected character')) {
          console.error('Unexpected character error detected - the stream may contain invalid JSON');
        }
        
        errorMessage = "Sorry, there was an error processing the response data. This might be due to a temporary issue with our servers. Please try again in a moment.";
      } else if (error.message && error.message.includes('No complete response received')) {
        console.error('No complete response received from the API');
        errorMessage = "We didn't receive a complete response from our servers. This might be due to a timeout or connection issue. Please try a shorter query or try again later.";
      } else if (error.message && error.message.includes('API request failed')) {
        errorMessage = "Sorry, we couldn't reach our servers. Please check your internet connection and try again.";
      } else if (error.message && error.message.includes('Response body is null')) {
        errorMessage = "We received an empty response from our servers. Please try again.";
      }
      
      // Show error message
      addMessage(errorMessage, 'bot', 'markdown', undefined, false);
      
      // Report the error to monitoring (if you have an error tracking service)
      console.error('Chat processing error details:', {
        errorType: error instanceof SyntaxError ? 'SyntaxError' : 'OtherError',
        errorMessage: error.message,
        timestamp: new Date().toISOString()
      });
    } finally {
      // Reset the processing flag
      processingRef.current = false;
    }
  };

  // Add a new message
  const addMessage = (
    content: string, 
    sender: 'user' | 'bot', 
    type: MessageType = 'text', 
    files?: FileObject[],
    hasCitations: boolean = false,
    processingSteps?: ProcessingStep[],
    citations?: Citation[]
  ) => {
    const newMessage: Message = {
      id: generateId(),
      sender,
      timestamp: Date.now(),
      content,
      type,
      files,
      hasCode: content.includes('```'),
      hasCitations: hasCitations,
      processingSteps: processingSteps,
      citations: citations
    };

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, newMessage],
      files: [], // Clear files after sending
    }));

    // Process user messages through the API only if not already processing
    if (sender === 'user' && type === 'text' && !processingRef.current) {
      processChat(content);
    }
  };

  // Add a file to be sent with the next message
  const addFile = (file: File) => {
    const fileObject: FileObject = {
      id: generateId(),
      name: file.name,
      type: file.type,
      url: URL.createObjectURL(file),
    };

    setState(prev => ({
      ...prev,
      files: [...prev.files, fileObject],
    }));
  };

  // Remove a file from the queue
  const removeFile = (fileId: string) => {
    setState(prev => ({
      ...prev,
      files: prev.files.filter(file => file.id !== fileId),
    }));
  };

  // Clear canvas content
  const clearCanvas = () => {
    setState(prev => ({
      ...prev,
      canvasContent: null,
    }));
  };

  // Add a function to clear chat and localStorage
  const clearChat = () => {
    // Clear localStorage
    localStorage.removeItem(CHAT_STORAGE_KEY);
    localStorage.removeItem(SESSION_ID_KEY);
    
    // Reset state
    setState({
      messages: [],
      isTyping: false,
      files: [],
      canvasContent: null,
      processingSteps: [],
      currentSession: undefined
    });
  };

  // Add regenerateMessage function
  const regenerateMessage = async (messageId: string) => {
    // Find the index of the message to regenerate
    const messageIndex = state.messages.findIndex(msg => msg.id === messageId);
    if (messageIndex === -1) return;

    const messageToRegenerate = state.messages[messageIndex];
    
    // Only allow regeneration of user messages
    if (messageToRegenerate.sender !== 'user') return;

    // Remove all messages that came after this message
    const updatedMessages = state.messages.slice(0, messageIndex + 1);
    
    // Update state and localStorage
    setState(prev => ({
      ...prev,
      messages: updatedMessages,
      processingSteps: [], // Clear any existing processing steps
    }));

    // Process the message again
    processChat(messageToRegenerate.content);
  };

  return {
    state,
    addMessage,
    addFile,
    removeFile,
    toggleCanvas,
    clearCanvas,
    clearMessages: clearChat,
    messagesEndRef,
    scrollToBottom,
    processChat,
    regenerateMessage
  };
};
