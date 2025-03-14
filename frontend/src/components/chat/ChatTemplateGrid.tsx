
import React from 'react';
import ChatTemplate from './ChatTemplate';
import { chatConfig } from '@/config/content';

interface ChatTemplateGridProps {
  onSelectTemplate: (prompt: string) => void;
}

const ChatTemplateGrid: React.FC<ChatTemplateGridProps> = ({ onSelectTemplate }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl w-full mx-auto">
      {chatConfig.templates.map((template, index) => (
        <ChatTemplate
          key={index}
          title={template.title}
          prompt={template.prompt}
          icon={template.icon}
          onClick={onSelectTemplate}
        />
      ))}
    </div>
  );
};

export default ChatTemplateGrid;
