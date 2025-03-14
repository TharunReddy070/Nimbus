import React from 'react';
import { X, FileText, Image as ImageIcon } from 'lucide-react';
import { FileObject } from '@/hooks/useChatState';

interface FilePreviewProps {
  files: FileObject[];
  onRemove: (fileId: string) => void;
}

const FilePreview: React.FC<FilePreviewProps> = ({ files, onRemove }) => {
  return (
    <div className="file-preview-container">
      {files.map(file => (
        <div key={file.id} className="file-preview-item group">
          <div className="flex items-center">
            {file.type.startsWith('image/') ? (
              <>
                <div className="file-preview-thumbnail">
                  <img src={file.url} alt={file.name} className="h-10 w-10 object-cover rounded" />
                </div>
                <span className="ml-2 text-sm truncate">{file.name}</span>
              </>
            ) : (
              <>
                <div className="file-preview-icon">
                  <FileText className="h-5 w-5" />
                </div>
                <span className="ml-2 text-sm truncate">{file.name}</span>
              </>
            )}
          </div>
          <button
            className="file-remove-button"
            onClick={() => onRemove(file.id)}
            aria-label="Remove file"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
};

export default FilePreview;
