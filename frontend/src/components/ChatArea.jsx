import React, { useRef, useEffect } from 'react';
import { Menu, Sparkles, FileText, Table, Zap, MessageSquare, Sun, Moon } from 'lucide-react';
import MessageItem from './MessageItem';
import InputBar from './InputBar';

export default function ChatArea({ 
  messages, 
  isLoading, 
  isUploading, 
  onSendMessage, 
  onFileUpload, 
  onToggleSidebar, 
  sidebarCollapsed,
  activeDoc,
  onOpenDocInspector,
  onSelectPrompt,
  theme,
  onToggleTheme
}) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, isUploading]);

  return (
    <main className="main-chat">
      {/* Top Header */}
      <header className="chat-header">
        <div className="header-left">
          {sidebarCollapsed && (
            <button className="icon-btn" onClick={onToggleSidebar} title="Mở sidebar">
              <Menu size={18} />
            </button>
          )}
          <div className="chat-title-group">
            <span className="chat-title">Hội thoại & Phân tích tài liệu</span>
            <span className="chat-subtitle">
              {activeDoc ? `Đang đối thoại về "${activeDoc.original_filename}"` : 'Google Gemini 2.5 Flash'}
            </span>
          </div>
        </div>

        <div className="header-badges">
          {activeDoc && (
            <div 
              className="active-doc-badge" 
              onClick={() => onOpenDocInspector(activeDoc)}
              title="Click để xem chi tiết Bảng & Text"
            >
              <FileText size={14} />
              <span>{activeDoc.original_filename}</span>
            </div>
          )}

          <button 
            className="icon-btn" 
            onClick={onToggleTheme} 
            title={`Chuyển sang ${theme === 'dark' ? 'Giao diện sáng' : 'Giao diện tối'}`}
          >
            {theme === 'dark' ? <Sun size={18} color="var(--accent-amber)" /> : <Moon size={18} color="var(--accent-indigo)" />}
          </button>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-hero">
            <div className="hero-icon">
              <Sparkles size={36} />
            </div>
            <h2 className="hero-title">Trợ lý AI & Trích xuất OCR</h2>
            <p className="hero-description">
              Tải lên hợp đồng, hóa đơn, chứng từ hoặc ảnh chụp để hệ thống tự động đọc, trích xuất bảng biểu 2D và tạo bản tóm tắt phân tích thông minh.
            </p>

            <div className="feature-cards-grid">
              <div className="feature-card" onClick={() => onSelectPrompt('Hướng dẫn cách upload và phân tích hợp đồng')}>
                <div className="feature-card-icon"><FileText size={20} /></div>
                <div className="feature-card-title">Hợp đồng & Pháp lý</div>
                <div className="feature-card-desc">Tự động trích xuất các bên tham gia, giá trị, thời hạn & nghĩa vụ.</div>
              </div>

              <div className="feature-card" onClick={() => onSelectPrompt('Cách trích xuất bảng biểu và tính toán số liệu')}>
                <div className="feature-card-icon"><Table size={20} /></div>
                <div className="feature-card-title">Tái tạo Bảng 2D</div>
                <div className="feature-card-desc">Chuyển đổi bảng từ PDF scan & Ảnh thành Markdown table sắc nét.</div>
              </div>

              <div className="feature-card" onClick={() => onSelectPrompt('Bạn hỗ trợ những định dạng file nào?')}>
                <div className="feature-card-icon"><Zap size={20} /></div>
                <div className="feature-card-title">Đa định dạng</div>
                <div className="feature-card-desc">Hỗ trợ PDF (Native & OCR Scan), Word DOCX, Excel XLSX và Ảnh.</div>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <MessageItem 
              key={idx} 
              message={msg} 
              onOpenDocInspector={onOpenDocInspector}
            />
          ))
        )}

        {/* Loading Indicator */}
        {(isLoading || isUploading) && (
          <div className="message-bubble ai">
            <div className="avatar ai">
              <Sparkles size={18} />
            </div>
            <div className="message-content-wrapper">
              <div className="message-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--accent-cyan)' }}>
                  <div className="typing-indicator">
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                  </div>
                  <span style={{ fontSize: '0.85rem' }}>
                    {isUploading ? 'Đang trích xuất dữ liệu tài liệu qua test-ocr & tạo bản tóm tắt...' : 'AI đang phân tích và trả lời...'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Section */}
      <InputBar 
        onSendMessage={onSendMessage}
        onFileUpload={onFileUpload}
        isLoading={isLoading}
        isUploading={isUploading}
        activeDoc={activeDoc}
      />
    </main>
  );
}
