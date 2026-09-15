import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Loader2 } from 'lucide-react';
import QuickPrompts from './QuickPrompts';

export default function InputBar({ onSendMessage, onFileUpload, isLoading, isUploading, activeDoc }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [text]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!text.trim() || isLoading || isUploading) return;
    onSendMessage(text);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files[0]);
      e.target.value = '';
    }
  };

  return (
    <div className="input-section">
      <QuickPrompts 
        onSelectPrompt={(prompt) => {
          setText(prompt);
          if (textareaRef.current) textareaRef.current.focus();
        }} 
        activeDoc={activeDoc} 
      />

      <div className="input-box-wrapper">
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          onChange={handleFileChange}
          accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.webp,.bmp,.txt"
        />

        <button 
          className="attach-btn" 
          onClick={() => fileInputRef.current?.click()} 
          title="Đính kèm file (PDF, DOCX, XLSX, Ảnh)"
          disabled={isLoading || isUploading}
        >
          <Paperclip size={18} />
        </button>

        <textarea
          ref={textareaRef}
          className="chat-textarea"
          rows={1}
          placeholder={
            isUploading 
              ? "Đang xử lý trích xuất tài liệu & OCR..." 
              : activeDoc 
                ? `Hỏi bất kỳ điều gì về "${activeDoc.original_filename}"...` 
                : "Nhập tin nhắn hoặc kéo thả tài liệu vào đây (Enter để gửi)..."
          }
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading || isUploading}
        />

        <div className="input-actions">
          <button 
            className="send-btn" 
            onClick={handleSubmit} 
            disabled={!text.trim() || isLoading || isUploading}
            title="Gửi câu hỏi"
          >
            {isLoading || isUploading ? (
              <Loader2 size={18} className="animate-spin" style={{ animation: 'bounce 1s infinite' }} />
            ) : (
              <Send size={16} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
