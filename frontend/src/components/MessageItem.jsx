import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User, FileText, ExternalLink, Copy, Check, AlertTriangle, AlertCircle } from 'lucide-react';


// ─── Main MessageItem ─────────────────────────────────────────────────────────
export default function MessageItem({ message, onOpenDocInspector }) {
  const isAi = message.role === 'assistant';
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Lấy metadata tài liệu & nội dung hiển thị sạch cho giao diện
  const docMeta = message.docResult || message.doc_result;
  let displayContent = message.displayContent || message.display_content || message.content;

  if (!isAi && typeof displayContent === 'string' && displayContent.includes('[HỆ THỐNG]:')) {
    // Nếu tin nhắn từ lịch sử chứa prompt hệ thống kèm OCR text thô
    const uploadMatchIndex = displayContent.lastIndexOf('Tải lên và');
    if (uploadMatchIndex !== -1) {
      displayContent = displayContent.substring(uploadMatchIndex);
    } else {
      const parts = displayContent.split('\n\n');
      displayContent = parts[parts.length - 1] || displayContent;
    }
  }

  // Kiểm tra nếu tin nhắn là thông báo lỗi
  const isError = message.isError || (isAi && typeof displayContent === 'string' && (displayContent.startsWith('❌') || displayContent.startsWith('⚠️')));

  if (isError) {
    const rawText = typeof displayContent === 'string' ? displayContent : '';
    let title = 'Thông báo lỗi hệ thống';
    if (rawText.includes('quá tải') || rawText.includes('Gemini API') || rawText.includes('429') || rawText.includes('giới hạn')) {
      title = 'Hệ thống tạm thời quá tải / Hết lượt dùng thử Gemini API';
    } else if (rawText.includes('API Key') || rawText.includes('Khóa API')) {
      title = 'Lỗi cấu hình khóa API (API Key)';
    } else if (rawText.includes('kết nối') || rawText.includes('mạng')) {
      title = 'Lỗi kết nối máy chủ AI';
    }

    const cleanContent = rawText.replace(/^(❌|⚠️)\s*(\*\*.*?\*\*:\s*)?/, '');

    return (
      <div className="message-bubble ai error-message-bubble">
        <div className="avatar ai error-avatar" style={{ background: 'var(--alert-bg)', border: '1px solid var(--alert-border)' }}>
          <AlertTriangle size={20} color="var(--alert-title-color)" />
        </div>

        <div className="message-content-wrapper">
          <div className="alert-box-card">
            <div className="alert-box-header">
              <AlertCircle size={18} className="alert-box-icon" />
              <span className="alert-box-title">{title}</span>
            </div>
            <div className="alert-box-body">
              {cleanContent}
            </div>
          </div>

          <div className="message-meta">
            <span>DocuMind AI</span>
            <span>•</span>
            <span>{message.time || 'Vừa xong'}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`message-bubble ${isAi ? 'ai' : 'user'}`}>
      <div className={`avatar ${isAi ? 'ai' : 'user'}`}>
        {isAi ? <Bot size={20} /> : <User size={20} />}
      </div>

      <div className="message-content-wrapper">
        <div className="message-card">
          {/* Document Attachment Badge */}
          {docMeta && (
            <div className="doc-card-badge">
              <FileText size={24} color="var(--accent-cyan)" />
              <div className="doc-badge-details">
                <div className="doc-badge-title">{docMeta.original_filename || 'Tài liệu'}</div>
                <div className="doc-badge-sub">
                  {docMeta.document_type?.toUpperCase()} • {docMeta.total_pages || 1} trang
                  {docMeta.tables && docMeta.tables.length > 0 && ` • ${docMeta.tables.length} bảng biểu`}
                </div>
              </div>
              {onOpenDocInspector && (
                <button
                  className="icon-btn"
                  onClick={() => onOpenDocInspector(docMeta)}
                  title="Xem chi tiết trích xuất & Bảng"
                >
                  <ExternalLink size={16} />
                </button>
              )}
            </div>
          )}

          {/* Markdown Content */}
          <div className="markdown-body">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                table: ({ node, ...props }) => (
                  <div className="table-wrapper">
                    <table {...props} />
                  </div>
                ),
              }}
            >
              {displayContent}
            </ReactMarkdown>
          </div>

        </div>

        {/* Message Meta Info */}
        <div className="message-meta">
          <span>{isAi ? 'DocuMind AI' : 'Bạn'}</span>
          <span>•</span>
          <span>{message.time || 'Vừa xong'}</span>
          {isAi && (
            <button
              onClick={handleCopy}
              style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '3px' }}
              title="Sao chép nội dung"
            >
              {copied ? <Check size={12} color="var(--accent-emerald)" /> : <Copy size={12} />}
              <span style={{ fontSize: '0.68rem' }}>{copied ? 'Đã sao chép' : 'Copy'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
