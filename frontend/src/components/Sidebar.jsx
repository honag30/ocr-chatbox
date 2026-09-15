import React, { useRef } from 'react';
import { 
  Sparkles, 
  UploadCloud, 
  Trash2, 
  ChevronLeft,
  Sun,
  Moon,
  MessageSquare,
  FolderOpen,
  Plus,
  Layers,
  FileText
} from 'lucide-react';

export default function Sidebar({ 
  collapsed, 
  onToggle, 
  activeTab,
  onTabChange,
  sessions,
  currentSessionId,
  onSelectSession,
  onCreateNewSession,
  onDeleteSession,
  onFileUpload, 
  onSelectFile, 
  onClearChat, 
  filesList, 
  isUploading,
  activeDoc,
  theme,
  onToggleTheme
}) {
  const fileInputRef = useRef(null);

  const getFileBadge = (ext) => {
    switch (ext) {
      case '.pdf':
        return <span className="file-icon-badge file-icon-pdf">PDF</span>;
      case '.docx':
        return <span className="file-icon-badge file-icon-docx">DOC</span>;
      case '.xlsx':
        return <span className="file-icon-badge file-icon-xlsx">XLS</span>;
      case '.png':
      case '.jpg':
      case '.jpeg':
      case '.webp':
      case '.bmp':
        return <span className="file-icon-badge file-icon-img">IMG</span>;
      default:
        return <span className="file-icon-badge">TXT</span>;
    }
  };

  const handleBoxClick = () => {
    if (fileInputRef.current && !isUploading) {
      fileInputRef.current.click();
    }
  };

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files[0]);
      e.target.value = '';
    }
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Header */}
      <div className="sidebar-header">
        <div className="brand">
          <div className="brand-icon">
            <Sparkles size={20} />
          </div>
          <div>
            <h1 className="brand-title">DocuMind</h1>
            <span className="brand-tag">OCR + Gemini</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button 
            className="icon-btn" 
            onClick={onToggleTheme} 
            title={`Chuyển sang ${theme === 'dark' ? 'Giao diện sáng' : 'Giao diện tối'}`}
          >
            {theme === 'dark' ? <Sun size={18} color="var(--accent-amber)" /> : <Moon size={18} color="var(--accent-indigo)" />}
          </button>
          <button className="icon-btn" onClick={onToggle} title="Thu gọn sidebar">
            <ChevronLeft size={18} />
          </button>
        </div>
      </div>

      {/* 2 Tabs Header */}
      <div className="sidebar-tabs">
        <button 
          className={`sidebar-tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => onTabChange('history')}
        >
          <MessageSquare size={15} />
          <span>Lịch sử chat</span>
        </button>
        <button 
          className={`sidebar-tab-btn ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => onTabChange('files')}
        >
          <FolderOpen size={15} />
          <span>Danh sách file ({filesList.length})</span>
        </button>
      </div>

      {/* Main Content Area based on Active Tab */}
      <div className="sidebar-content">
        {activeTab === 'history' ? (
          /* TAB 1: Lịch sử trò chuyện */
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <button className="new-chat-btn" onClick={onCreateNewSession} title="Tạo cuộc trò chuyện mới">
              <Plus size={16} />
              <span>Cuộc trò chuyện mới</span>
            </button>

            <div className="section-label" style={{ marginTop: '12px' }}>
              <MessageSquare size={13} />
              <span>Các cuộc trò chuyện gần đây</span>
            </div>

            <div className="sidebar-scroll-list">
              {sessions.length === 0 ? (
                <div className="sidebar-empty-state">
                  Chưa có lịch sử trò chuyện nào
                </div>
              ) : (
                sessions.map((sess) => (
                  <div 
                    key={sess.session_id} 
                    className={`session-item ${currentSessionId === sess.session_id ? 'active' : ''}`}
                    onClick={() => onSelectSession(sess.session_id)}
                    title={sess.title}
                  >
                    <div className="session-item-content">
                      <MessageSquare size={15} className="session-icon" />
                      <div className="session-info">
                        <div className="session-title">{sess.title || 'Cuộc trò chuyện mới'}</div>
                        <div className="session-meta">
                          {sess.updated_at ? sess.updated_at.slice(5, 16) : ''}
                          {sess.message_count ? ` • ${sess.message_count} tin` : ''}
                        </div>
                      </div>
                    </div>
                    <button 
                      className="session-delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(sess.session_id);
                      }}
                      title="Xóa cuộc trò chuyện"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : (
          /* TAB 2: Danh sách file tải lên */
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Upload Action */}
            <div style={{ marginBottom: '12px' }}>
              <div className="section-label">
                <UploadCloud size={13} />
                <span>Tải lên tài liệu mới</span>
              </div>
              <div 
                className="upload-action-box" 
                onClick={handleBoxClick}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  style={{ display: 'none' }} 
                  onChange={handleInputChange}
                  accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.webp,.bmp,.txt"
                />
                <div className="upload-icon-wrapper">
                  <UploadCloud size={20} />
                </div>
                <div className="upload-title">
                  {isUploading ? 'Đang trích xuất OCR...' : 'Chọn hoặc Kéo thả file'}
                </div>
                <div className="upload-subtitle">
                  PDF, Word, Excel, Ảnh hóa đơn/chứng từ
                </div>
              </div>
            </div>

            {/* Server Files List */}
            <div className="section-label">
              <Layers size={13} />
              <span>Tài liệu trên Server ({filesList.length})</span>
            </div>

            <div className="sidebar-scroll-list">
              {filesList.length === 0 ? (
                <div className="sidebar-empty-state">
                  Đang quét danh sách file...
                </div>
              ) : (
                filesList.map((file, idx) => (
                  <div 
                    key={idx} 
                    className={`file-item ${activeDoc?.original_filename === file.name ? 'active' : ''}`}
                    onClick={() => onSelectFile(file.path)}
                    title={`Click để tóm tắt: ${file.name}`}
                  >
                    <div className="file-info">
                      {getFileBadge(file.extension)}
                      <div>
                        <div className="file-name">{file.name}</div>
                        <div className="file-category">
                          {file.category} • {(file.size / 1024).toFixed(0)} KB
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <button className="btn-secondary" onClick={onClearChat} title="Xóa tất cả tin nhắn trong phiên này">
          <Trash2 size={15} />
          <span>Xóa tin nhắn hiện tại</span>
        </button>
        <div className="system-status">
          <div className="status-indicator">
            <span className="status-dot"></span>
            <span>Gemini 2.5 Flash + OCR</span>
          </div>
          <span>Sẵn sàng</span>
        </div>
      </div>
    </aside>
  );
}
