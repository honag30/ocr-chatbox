import React from 'react';
import { HelpCircle, DollarSign, FileCheck, Users, Calendar, AlertTriangle } from 'lucide-react';

export default function QuickPrompts({ onSelectPrompt, activeDoc }) {
  const documentPrompts = [
    { icon: <Users size={12} />, text: 'Bên A và Bên B là những ai?' },
    { icon: <DollarSign size={12} />, text: 'Tổng số tiền và phương thức thanh toán là gì?' },
    { icon: <Calendar size={12} />, text: 'Thời hạn hợp đồng và các mốc thời gian quan trọng?' },
    { icon: <FileCheck size={12} />, text: 'Liệt kê các nghĩa vụ chính của mỗi bên' },
    { icon: <AlertTriangle size={12} />, text: 'Có điều khoản phạt vi phạm hay rủi ro gì không?' },
  ];

  const generalPrompts = [
    { icon: <HelpCircle size={12} />, text: 'Bạn có thể giúp tôi đọc những loại tài liệu nào?' },
    { icon: <FileCheck size={12} />, text: 'Hướng dẫn cách upload và phân tích hóa đơn' },
    { icon: <DollarSign size={12} />, text: 'Cách trích xuất dữ liệu bảng từ file PDF/Ảnh' },
  ];

  const prompts = activeDoc ? documentPrompts : generalPrompts;

  return (
    <div className="quick-prompts-bar">
      {prompts.map((p, idx) => (
        <button 
          key={idx} 
          className="quick-prompt-btn" 
          onClick={() => onSelectPrompt(p.text)}
        >
          {p.icon}
          <span>{p.text}</span>
        </button>
      ))}
    </div>
  );
}
