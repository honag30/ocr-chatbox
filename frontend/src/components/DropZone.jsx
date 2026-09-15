import React from 'react';
import { UploadCloud, FileSpreadsheet, FileText, Image as ImageIcon } from 'lucide-react';

export default function DropZone({ isDragging }) {
  if (!isDragging) return null;

  return (
    <div className="drop-overlay">
      <div className="drop-box">
        <div className="drop-icon">
          <UploadCloud size={40} />
        </div>
        <h2 style={{ fontSize: '1.4rem', fontWeight: '700', color: '#fff' }}>
          Thả tài liệu vào đây để xử lý
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', maxWidth: '420px' }}>
          Hệ thống sẽ tự động trích xuất nội dung bằng <strong style={{ color: 'var(--accent-cyan)' }}>test-ocr</strong> và phân tích tóm tắt bằng <strong style={{ color: 'var(--accent-cyan)' }}>Gemini AI</strong>.
        </p>
        <div style={{ display: 'flex', gap: '16px', marginTop: '10px', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><FileText size={14} /> PDF / DOCX</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><FileSpreadsheet size={14} /> XLSX</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><ImageIcon size={14} /> PNG / JPG / Scan</span>
        </div>
      </div>
    </div>
  );
}
