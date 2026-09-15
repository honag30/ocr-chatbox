import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import DropZone from './components/DropZone';
import DocInspector from './components/DocInspector';

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
      const res = await fetch('/api/files');
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
      const res = await fetch('/api/sessions');
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
      const res = await fetch('/api/history');
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
      const res = await fetch('/api/sessions/switch', {
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
      const res = await fetch('/api/sessions', { method: 'POST' });
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
      const res = await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
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
      const res = await fetch('/api/chat', {
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
        res = await fetch('/api/upload', {
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

      // Thêm message thông báo upload và tóm tắt
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
    if (isUploading) return;
    setIsUploading(true);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 phút timeout

      let res;
      try {
        res = await fetch('/api/select-file', {
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
      await fetch('/api/clear', { method: 'POST' });
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

      {inspectorDoc && (
        <DocInspector 
          docResult={inspectorDoc} 
          onClose={() => setInspectorDoc(null)} 
        />
      )}
    </div>
  );
}
