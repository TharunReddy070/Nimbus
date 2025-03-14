import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import './CanvasView.css';

interface CanvasViewProps {
  content: string;
}

// Error boundary component
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return <div>Something went wrong rendering Markdown.</div>;
    }

    return this.props.children;
  }
}

const CanvasView: React.FC<CanvasViewProps> = ({ content }) => {
  // Clean up any problematic characters or patterns
  const cleanContent = content
    ? content
        .replace(/data-lov-id="[^"]*"/g, '')
        .replace(/\\n/g, '\n') // Convert escaped newlines to actual newlines
        .trim()
    : '';
  
  // Debug the content being received
  console.log('Markdown content length:', cleanContent.length);
  if (cleanContent.includes('##')) {
    console.log('Content contains ## characters');
  }
  
  return (
    <div className="canvas-container">
      <div className="markdown">
        {!cleanContent ? (
          <p>No content to display</p>
        ) : (
          <ErrorBoundary>
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]} 
              rehypePlugins={[rehypeRaw, rehypeSanitize]}
            >
              {cleanContent}
            </ReactMarkdown>
          </ErrorBoundary>
        )}
      </div>
    </div>
  );
};

export default CanvasView;
