import React, { useState } from 'react';
import { X, Cpu, Layers } from 'lucide-react';

/**
 * Render một element văn bản theo type (heading | list | paragraph | table)
 * để bảo toàn format tương đối gần bản gốc.
 */
function DocElement({ el, idx }) {
  if (!el || !el.text) return null;

  if (el.type === 'heading') {
    return (
      <div key={idx} style={{
        fontWeight: 700,
        fontSize: '0.82rem',
        color: 'var(--text-main)',
        letterSpacing: '0.03em',
        marginTop: '14px',
        marginBottom: '4px',
        textAlign: 'center',
        lineHeight: 1.5,
      }}>
        {el.text}
      </div>
    );
  }

  if (el.type === 'list') {
    return (
      <div key={idx} style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '8px',
        paddingLeft: '16px',
        marginBottom: '3px',
        lineHeight: 1.65,
      }}>
        <span style={{ color: 'var(--accent-cyan)', flexShrink: 0, marginTop: '2px', fontSize: '0.7rem' }}>•</span>
        <span style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>{el.text.replace(/^[•\-\*\+]\s+/, '').replace(/^\d+\.\d+(\.\d+)?\s+/, '').replace(/^[a-z]\)\s+/, '')}</span>
      </div>
    );
  }

  if (el.type === 'table') {
    // Hiển thị bảng đơn giản nếu element là table inline
    return (
      <div key={idx} style={{ margin: '8px 0', fontSize: '0.75rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
        [Bảng — xem chi tiết ở tab Bảng biểu]
      </div>
    );
  }

  // paragraph (default)
  return (
    <div key={idx} style={{
      fontSize: '0.775rem',
      color: 'var(--text-muted)',
      lineHeight: 1.75,
      marginBottom: '2px',
      textAlign: 'justify',
      wordBreak: 'break-word',
    }}>
      {el.text}
    </div>
  );
}

export default function DocInspector({ docResult, onClose }) {
  if (!docResult) return null;

  const [activeTab, setActiveTab] = useState('meta');
  const tables = docResult.tables || [];

  return (
    <aside className="inspector-drawer">
      <div className="inspector-header">
        <div className="inspector-title">
          <Layers size={18} color="var(--accent-cyan)" />
          <span>Chi tiết trích xuất OCR</span>
        </div>
        <button className="icon-btn" onClick={onClose} title="Đóng">
          <X size={18} />
        </button>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid var(--border-glass)', padding: '0 16px' }}>
        <button 
          onClick={() => setActiveTab('meta')}
          style={{
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'meta' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
            color: activeTab === 'meta' ? 'var(--accent-cyan)' : 'var(--text-muted)',
            padding: '10px 14px',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Cpu size={14} />
          <span>Thông số</span>
        </button>
      </div>

      <div className="inspector-content">
        {/* TAB: META INFO */}
        {activeTab === 'meta' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="stat-grid">
              <div className="stat-card">
                <div className="stat-label">Tên File</div>
                <div className="stat-value" style={{ fontSize: '0.8rem', wordBreak: 'break-all' }}>
                  {docResult.original_filename}
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-label">Định dạng</div>
                <div className="stat-value">{docResult.document_type?.toUpperCase()}</div>
              </div>

              <div className="stat-card">
                <div className="stat-label">Số trang / sheet</div>
                <div className="stat-value">{docResult.total_pages || 1}</div>
              </div>

              <div className="stat-card">
                <div className="stat-label">Số lượng Bảng</div>
                <div className="stat-value">{tables.length}</div>
              </div>

              <div className="stat-card">
                <div className="stat-label">Nguồn dữ liệu</div>
                <div className="stat-value" style={{ fontSize: '0.8rem' }}>{docResult.source_type}</div>
              </div>

              <div className="stat-card">
                <div className="stat-label">Phương pháp đọc</div>
                <div className="stat-value" style={{ fontSize: '0.8rem', color: 'var(--accent-emerald)' }}>
                  {docResult.extraction_method}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
