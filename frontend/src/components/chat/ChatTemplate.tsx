
import React from 'react';
import { cn } from '@/lib/utils';
import { Cloud, ArrowRightLeft, DollarSign, Network } from 'lucide-react';

// Map icon names to components
const iconMap = {
  Cloud,
  ArrowRightLeft,
  DollarSign,
  Network
};

interface ChatTemplateProps {
  title: string;
  prompt: string;
  icon: string;
  onClick: (prompt: string) => void;
}

const ChatTemplate: React.FC<ChatTemplateProps> = ({ title, prompt, icon, onClick }) => {
  // Get the appropriate icon component
  const IconComponent = iconMap[icon as keyof typeof iconMap];

  return (
    <button 
      className={cn(
        "flex flex-col items-start w-full p-4 rounded-lg border border-gray-200",
        "hover:bg-gray-50 hover:border-primary/50 transition-all",
        "text-left"
      )}
      onClick={() => onClick(prompt)}
    >
      <div className="flex items-center mb-3">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mr-3">
          {IconComponent && <IconComponent className="h-5 w-5 text-primary" />}
        </div>
        <p className="mb-1 text-lg font-medium">{title}</p>
      </div>
      <p className="text-sm text-gray-500 line-clamp-2">{prompt}</p>
    </button>
  );
};

export default ChatTemplate;
