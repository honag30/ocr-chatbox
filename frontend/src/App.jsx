import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import DropZone from './components/DropZone';
import DocInspector from './components/DocInspector';
import EvidenceInspector from './components/EvidenceInspector';

/**
 * Đọc JSON từ response một cách an toàn.
 * Trả về null nếu response rỗng hoặc không phải JSON hợp lệ.
 */
async function safeJson(res) {
  const text = await res.text();
  if (!text || text.trim() === '') return null;
  try {
    return JSON.parse(text);
  } catch {
    console.error('Không thể parse JSON từ server:', text.slice(0, 300));
    return null;
  }
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [activeTab, setActiveTab] = useState('history'); // 'history' | 'files'
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [filesList, setFilesList] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeDoc, setActiveDoc] = useState(null);
  const [inspectorDoc, setInspectorDoc] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  // Sync theme with html root element & localStorage
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Fetch initial history, sessions and files list
  useEffect(() => {
    fetchFiles();
    fetchSessions();
    fetchHistory();
  }, []);

  const fetchFiles = async () => {
    try {
      const res = await fetch('/api/document/files');
      const data = await res.json();
      if (data.status === 'success') {
        setFilesList(data.files || []);
      }
    } catch (err) {
      console.error('Lỗi khi tải danh sách files:', err);
    }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch('/api/chatbox/sessions');
      const data = await res.json();
      if (data.status === 'success') {
        setSessions(data.sessions || []);
        if (data.current_session_id) {
          setCurrentSessionId(data.current_session_id);
        }
      }
    } catch (err) {
      console.error('Lỗi khi tải danh sách sessions:', err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/chatbox/history');
      const data = await res.json();
      if (data.status === 'success') {
        if (data.session_id) {
          setCurrentSessionId(data.session_id);
        }
        if (data.messages) {
          setMessages(
            data.messages.map((m) => ({
              role: m.role,
              content: m.content,
              isError: m.isError || (m.role === 'assistant' && (m.content.startsWith('❌') || m.content.startsWith('⚠️'))),
              displayContent: m.display_content || m.content,
              docResult: m.doc_result || m.docResult || null,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            }))
          );
        }
        if (data.active_doc) {
          setActiveDoc(data.active_doc);
        }
      }
    } catch (err) {
      console.error('Lỗi khi tải lịch sử:', err);
    }
  };

  const handleSelectSession = async (sessionId) => {
    if (sessionId === currentSessionId) return;
    try {
      const res = await fetch('/api/chatbox/sessions/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setCurrentSessionId(sessionId);
        setMessages(
          (data.messages || []).map((m) => ({
            role: m.role,
            content: m.content,
            isError: m.isError || (m.role === 'assistant' && (m.content.startsWith('❌') || m.content.startsWith('⚠️'))),
            displayContent: m.display_content || m.content,
            docResult: m.doc_result || m.docResult || null,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }))
        );
        setActiveDoc(data.active_doc || null);
      }
    } catch (err) {
      console.error('Lỗi khi chuyển phiên chat:', err);
    }
  };

  const handleCreateNewSession = async () => {
    try {
      const res = await fetch('/api/chatbox/sessions', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setCurrentSessionId(data.session_id);
        setMessages([]);
        setActiveDoc(null);
        setInspectorDoc(null);
        fetchSessions();
      }
    } catch (err) {
      console.error('Lỗi khi tạo phiên chat mới:', err);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      const res = await fetch(`/api/chatbox/sessions/${sessionId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.status === 'success') {
        setSessions(data.sessions || []);
        if (data.current_session_id) {
          setCurrentSessionId(data.current_session_id);
          setMessages(
            (data.messages || []).map((m) => ({
              role: m.role,
              content: m.content,
              isError: m.isError || (m.role === 'assistant' && (m.content.startsWith('❌') || m.content.startsWith('⚠️'))),
              displayContent: m.display_content || m.content,
              docResult: m.doc_result || m.docResult || null,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            }))
          );
          setActiveDoc(data.active_doc || null);
        }
      }
    } catch (err) {
      console.error('Lỗi khi xóa phiên chat:', err);
    }
  };

  const handleSendMessage = async (text) => {
    if (!text.trim() || isLoading) return;

    const userMsg = {
      role: 'user',
      content: text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await fetch('/api/chatbox/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });

      const data = await safeJson(res);
      if (!data) throw new Error(`Server trả về phản hồi không hợp lệ (HTTP ${res.status})`);
      if (!res.ok) throw new Error(data.detail || 'Lỗi từ server');

      const aiMsg = {
        role: 'assistant',
        content: data.answer,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, aiMsg]);
      fetchSessions(); // Refresh sessions list title & timestamp
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        isError: true,
        content: err.message,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const [evidencePackage, setEvidencePackage] = useState(null);
  const [isExtractingEvidence, setIsExtractingEvidence] = useState(false);
  const [evidenceError, setEvidenceError] = useState(null);

  const handleFileUpload = async (file, instruction = '') => {
    if (!file || isUploading) return;

    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file);
    if (instruction) {
      formData.append('instruction', instruction);
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 phút timeout

      let res;
      try {
        res = await fetch('/api/document/upload', {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        });
      } finally {
        clearTimeout(timeoutId);
      }

      const data = await safeJson(res);
      if (!data) throw new Error(`Server trả về phản hồi không hợp lệ (HTTP ${res.status}). Có thể file quá lớn hoặc OCR thất bại.`);
      if (!res.ok) throw new Error(data.detail || 'Lỗi khi upload file');

      setActiveDoc(data.doc_result);
      setEvidencePackage(null);

      // Thêm message thông báo upload và tóm tắt nếu không ở tab Evidence
      if (activeTab !== 'evidence') {
        const userMsg = {
          role: 'user',
          content: `Tải lên và phân tích tài liệu: **${data.filename}**`,
          docResult: data.doc_result,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };

        const aiMsg = {
          role: 'assistant',
          content: data.summary,
          docResult: data.doc_result,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };

        setMessages((prev) => [...prev, userMsg, aiMsg]);
      }

      fetchFiles(); // Refresh file list
      fetchSessions(); // Refresh sessions list
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        isError: true,
        content: err.message,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSelectFile = async (filePath) => {
    if (isUploading || isExtractingEvidence) return;

    const fileName = filePath.split(/[/\\]/).pop();
    const docObj = { file_path: filePath, original_filename: fileName };
    setActiveDoc(docObj);

    // Nếu đang ở tab Evidence, chỉ trích xuất Evidence Truth không chạy tóm tắt Chat
    if (activeTab === 'evidence') {
      setEvidencePackage(null);
      handleExtractEvidence(filePath);
      return;
    }

    setIsUploading(true);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 phút timeout

      let res;
      try {
        res = await fetch('/api/document/select-file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_path: filePath }),
          signal: controller.signal,
        });
      } finally {
        clearTimeout(timeoutId);
      }

      const data = await safeJson(res);
      if (!data) throw new Error(`Server trả về phản hồi không hợp lệ (HTTP ${res.status}). Có thể OCR thất bại hoặc file không hợp lệ.`);
      if (!res.ok) throw new Error(data.detail || 'Lỗi khi đọc file');

      setActiveDoc(data.doc_result);

      const userMsg = {
        role: 'user',
        content: `Tải lên và tóm tắt: **${data.filename}**`,
        docResult: data.doc_result,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      const aiMsg = {
        role: 'assistant',
        content: data.summary,
        docResult: data.doc_result,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, userMsg, aiMsg]);
      fetchSessions();
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        isError: true,
        content: err.message,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleClearChat = async () => {
    try {
      await fetch('/api/chatbox/clear', { method: 'POST' });
      setMessages([]);
      setActiveDoc(null);
      setInspectorDoc(null);
      fetchSessions();
    } catch (err) {
      console.error('Lỗi khi xóa lịch sử:', err);
    }
  };

  // Drag and Drop listeners
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  // Reset evidencePackage when activeDoc changes
  useEffect(() => {
    setEvidencePackage(null);
  }, [activeDoc]);

  // Trigger evidence extraction when activeDoc or activeTab changes
  useEffect(() => {
    if (activeTab === 'evidence' && !evidencePackage && !isExtractingEvidence) {
      handleExtractEvidence();
    }
  }, [activeDoc, activeTab, evidencePackage]);

  const handleExtractEvidence = async (targetFilePath = null) => {
    let filePath = targetFilePath || (activeDoc ? (activeDoc.file_path || activeDoc.original_filename) : null);
    if (!filePath && filesList && filesList.length > 0) {
      filePath = filesList[0].path || filesList[0].name;
      const fileName = filePath.split(/[/\\]/).pop();
      setActiveDoc({ file_path: filePath, original_filename: fileName });
    }
    if (!filePath) {
      setEvidenceError('Vui lòng chọn một tài liệu từ danh sách bên trái hoặc tải file mới lên.');
      return;
    }
    setIsExtractingEvidence(true);
    setEvidenceError(null);
    try {
      const res = await fetch('/api/evidence/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: filePath })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Lỗi từ server khi bóc tách Evidence (HTTP ${res.status})`);
      }
      setEvidencePackage(data);
      setEvidenceError(null);
    } catch (err) {
      console.error('Lỗi khi bóc tách Evidence:', err);
      setEvidenceError(err.message);
    } finally {
      setIsExtractingEvidence(false);
    }
  };

  const handleVerifyEvidence = async (pkgId) => {
    try {
      const res = await fetch(`/api/evidence/${pkgId}/verify`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setEvidencePackage(prev => prev ? {
          ...prev,
          trust: { ...prev.trust, verification_status: 'VERIFIED', review_required: false, publish_status: 'ELIGIBLE' }
        } : null);
      }
    } catch (err) {
      console.error('Lỗi khi verify Evidence:', err);
    }
  };

  const handleRejectEvidence = async (pkgId) => {
    try {
      const res = await fetch(`/api/evidence/${pkgId}/reject`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setEvidencePackage(prev => prev ? {
          ...prev,
          trust: { ...prev.trust, verification_status: 'REJECTED', review_required: false, publish_status: 'BLOCKED' }
        } : null);
      }
    } catch (err) {
      console.error('Lỗi khi reject Evidence:', err);
    }
  };

  const handlePublishEvidence = async (pkgId) => {
    try {
      const res = await fetch(`/api/evidence/${pkgId}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'PUBLISHED' })
      });
      const data = await res.json();
      if (res.ok) {
        setEvidencePackage(prev => prev ? {
          ...prev,
          trust: { ...prev.trust, publish_status: 'PUBLISHED' }
        } : null);
      }
    } catch (err) {
      console.error('Lỗi khi publish Evidence:', err);
    }
  };

  return (
    <div 
      className="app-container"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <DropZone isDragging={isDragging} />

      <Sidebar 
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onCreateNewSession={handleCreateNewSession}
        onDeleteSession={handleDeleteSession}
        onFileUpload={handleFileUpload}
        onSelectFile={handleSelectFile}
        onClearChat={handleClearChat}
        filesList={filesList}
        isUploading={isUploading}
        activeDoc={activeDoc}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {activeTab === 'evidence' ? (
        <EvidenceInspector
          evidencePackage={evidencePackage}
          isExtracting={isExtractingEvidence}
          activeDoc={activeDoc}
          filesList={filesList}
          error={evidenceError}
          onSelectFile={handleSelectFile}
          onFileUpload={handleFileUpload}
          onVerify={handleVerifyEvidence}
          onReject={handleRejectEvidence}
          onPublish={handlePublishEvidence}
          onExtractNew={handleExtractEvidence}
        />
      ) : (
        <ChatArea 
          messages={messages}
          isLoading={isLoading}
          isUploading={isUploading}
          onSendMessage={handleSendMessage}
          onFileUpload={handleFileUpload}
          onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
          sidebarCollapsed={sidebarCollapsed}
          activeDoc={activeDoc}
          onOpenDocInspector={(doc) => setInspectorDoc(doc)}
          onSelectPrompt={handleSendMessage}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
      )}

      {inspectorDoc && (
        <DocInspector 
          docResult={inspectorDoc} 
          onClose={() => setInspectorDoc(null)} 
        />
      )}
    </div>
  );
}
