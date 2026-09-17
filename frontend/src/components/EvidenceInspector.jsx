import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  UploadCloud,
  FileText,
  DollarSign,
  TrendingUp,
  Award,
  Share2,
  Search,
  ExternalLink,
  Layers,
  ArrowRight,
  Loader2
} from 'lucide-react';

export default function EvidenceInspector({
  evidencePackage,
  isExtracting = false,
  activeDoc = null,
  filesList = [],
  error = null,
  onSelectFile,
  onFileUpload,
  onVerify,
  onReject,
  onPublish,
  onExtractNew
}) {
  const [selectedFact, setSelectedFact] = useState(null);
  const [activeTab, setActiveTab] = useState('facts'); // 'facts', 'economic', 'cashflow', 'funding', 'graph'
  const fileInputRef = React.useRef(null);

  if (isExtracting) {
    return (
      <div className="evidence-empty-state">
        <div className="evidence-empty-icon">
          <Loader2 size={40} color="var(--accent-emerald, #10b981)" className="spinning" />
        </div>
        <h2 style={{ marginTop: '16px' }}>Đang bóc tách Evidence Truth...</h2>
        <p>Hệ thống đang trích xuất Facts, Ý nghĩa kinh tế, Dòng tiền & Đồ thị liên kết từ tài liệu...</p>
      </div>
    );
  }

  if (!evidencePackage) {
    const currentFileName = activeDoc?.original_filename || (activeDoc?.file_path ? activeDoc.file_path.split(/[/\\]/).pop() : null);

    return (
      <div className="evidence-empty-state">
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }}
          accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.webp,.txt"
          onChange={(e) => {
            if (e.target.files && e.target.files[0] && onFileUpload) {
              onFileUpload(e.target.files[0]);
            }
          }} 
        />
        <div className="evidence-empty-icon">
          <ShieldAlert size={40} color="var(--accent-amber)" />
        </div>
        <h2>Evidence Extraction Engine</h2>
        <p style={{ maxWidth: '580px', margin: '10px auto 22px auto', color: 'var(--text-muted)', lineHeight: '1.6' }}>
          {currentFileName ? (
            <>
              Tài liệu sẵn sàng: <strong style={{ color: 'var(--accent-cyan)' }}>{currentFileName}</strong>.<br />
              Bấm nút bên dưới để bóc tách toàn diện Facts, Ý nghĩa kinh tế, Dòng tiền & Đồ thị thực thể.
            </>
          ) : (
            'Chưa có tài liệu nào được chọn. Hãy chọn một tài liệu từ kho lưu trữ bên trái hoặc tải file mới lên để bóc tách Evidence Truth.'
          )}
        </p>
        {error && (
          <div className="evidence-alert-box alert-warning" style={{ maxWidth: '580px', margin: '0 auto 20px auto', textAlign: 'left', border: '1px solid rgba(244, 63, 94, 0.4)', background: 'rgba(244, 63, 94, 0.12)', color: 'var(--accent-rose)' }}>
            <AlertTriangle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <strong style={{ display: 'block', marginBottom: '4px' }}>Thông báo lỗi</strong>
              <span>{error}</span>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', justifyContent: 'center' }}>
          {currentFileName ? (
            <button className="btn-primary" onClick={() => onExtractNew && onExtractNew()}>
              <UploadCloud size={18} />
              <span>Bóc tách Evidence: {currentFileName}</span>
            </button>
          ) : (
            <>
              <button className="btn-primary" onClick={() => fileInputRef.current?.click()}>
                <UploadCloud size={18} />
                <span>Tải tài liệu mới lên</span>
              </button>
              {filesList && filesList.length > 0 && (
                <button 
                  className="btn-secondary" 
                  onClick={() => {
                    const firstFile = filesList[0];
                    const p = firstFile.path || firstFile.name;
                    if (onSelectFile) onSelectFile(p);
                    else if (onExtractNew) onExtractNew(p);
                  }}
                >
                  <FileText size={18} />
                  <span>Trích xuất: {filesList[0].name}</span>
                </button>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  const {
    evidence_package_id,
    document: doc,
    evidence_facts = [],
    economic_artifacts = [],
    object_bindings = [],
    document_relationships = [],
    cashflow_relevance = {},
    funding_relevance = {},
    trust = {},
    provenance = {},
    lineage = {},
    conflicts = []
  } = evidencePackage;

  const verifStatus = trust.verification_status || 'UNVERIFIED';
  const pubStatus = trust.publish_status || 'PENDING';
  const overallConf = trust.confidence?.overall ? (trust.confidence.overall * 100).toFixed(0) : 0;

  return (
    <div className="evidence-container">
      {/* Header Bar */}
      <div className="evidence-header">
        <div className="evidence-title-group">
          <div className="evidence-badge-icon">
            <ShieldCheck size={24} color="var(--accent-emerald)" />
          </div>
          <div>
            <div className="evidence-pkg-id">ID: {evidence_package_id}</div>
            <h2 className="evidence-heading">Evidence Extraction Result</h2>
          </div>
        </div>

        <div className="evidence-status-actions">
          <div className={`status-pill status-${verifStatus.toLowerCase()}`}>
            {verifStatus === 'VERIFIED' && <CheckCircle2 size={14} />}
            {verifStatus === 'REJECTED' && <XCircle size={14} />}
            {verifStatus === 'REVIEW_REQUIRED' && <AlertTriangle size={14} />}
            <span>Thẩm định: {verifStatus}</span>
          </div>

          <div className={`status-pill status-${pubStatus.toLowerCase()}`}>
            <span>DataHub: {pubStatus}</span>
          </div>

          <div className="evidence-btn-group">
            {verifStatus !== 'VERIFIED' && (
              <button className="btn-success-sm" onClick={() => onVerify(evidence_package_id)}>
                <CheckCircle2 size={14} />
                <span>Xác nhận Truth</span>
              </button>
            )}
            {verifStatus !== 'REJECTED' && (
              <button className="btn-danger-sm" onClick={() => onReject(evidence_package_id)}>
                <XCircle size={14} />
                <span>Từ chối</span>
              </button>
            )}
            {verifStatus === 'VERIFIED' && pubStatus !== 'PUBLISHED' && (
              <button className="btn-primary-sm" onClick={() => onPublish(evidence_package_id)}>
                <Share2 size={14} />
                <span>Xuất bản sang DataHub</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Conflict Banner Alert if present */}
      {conflicts && conflicts.length > 0 && (
        <div className="evidence-alert-box alert-warning">
          <AlertTriangle size={20} />
          <div>
            <strong>Phát hiện Mâu thuẫn Dữ liệu (Conflict Detected):</strong>
            <ul>
              {conflicts.map((c, i) => (
                <li key={i}>
                  Trường <code>{c.field}</code>: {c.description}
                  <div className="conflict-values">
                    {c.values.map((v, j) => (
                      <span key={j} className="conflict-tag">
                        {String(v.value)} ({v.source})
                      </span>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Section 1 — Document Information */}
      <div className="evidence-card document-section">
        <div className="card-title">
          <FileText size={18} />
          <span>Section 1 — Document Metadata</span>
        </div>
        <div className="doc-grid">
          <div className="doc-field">
            <span className="field-label">Document Type</span>
            <span className="field-val doc-type-badge">{doc?.document_type || 'UNKNOWN'}</span>
          </div>
          <div className="doc-field">
            <span className="field-label">Document Number</span>
            <span className="field-val">{doc?.document_number || 'N/A'}</span>
          </div>
          <div className="doc-field">
            <span className="field-label">Document Date</span>
            <span className="field-val">{doc?.document_date || 'N/A'}</span>
          </div>
          <div className="doc-field">
            <span className="field-label">Organization</span>
            <span className="field-val">{doc?.organization_id || 'ORG-DEFAULT'}</span>
          </div>
          <div className="doc-field">
            <span className="field-label">AI Confidence</span>
            <span className="field-val conf-val">{overallConf}%</span>
          </div>
        </div>
      </div>

      {/* Sub-tabs for Sections 2-6 */}
      <div className="evidence-tabs">
        <button
          className={`evidence-tab ${activeTab === 'facts' ? 'active' : ''}`}
          onClick={() => setActiveTab('facts')}
        >
          <Layers size={15} />
          <span>Section 2 — Extracted Facts ({evidence_facts.length})</span>
        </button>
        <button
          className={`evidence-tab ${activeTab === 'economic' ? 'active' : ''}`}
          onClick={() => setActiveTab('economic')}
        >
          <DollarSign size={15} />
          <span>Section 3 — Economic Meaning</span>
        </button>
        <button
          className={`evidence-tab ${activeTab === 'cashflow' ? 'active' : ''}`}
          onClick={() => setActiveTab('cashflow')}
        >
          <TrendingUp size={15} />
          <span>Section 4 — Cash Flow Impact</span>
        </button>
        <button
          className={`evidence-tab ${activeTab === 'funding' ? 'active' : ''}`}
          onClick={() => setActiveTab('funding')}
        >
          <Award size={15} />
          <span>Section 5 — Funding Relevance</span>
        </button>
        <button
          className={`evidence-tab ${activeTab === 'graph' ? 'active' : ''}`}
          onClick={() => setActiveTab('graph')}
        >
          <Share2 size={15} />
          <span>Section 6 — Graph & Lineage</span>
        </button>
      </div>

      {/* TAB CONTENT */}
      <div className="evidence-tab-body">
        {/* TAB 1: EXTRACTED FACTS TABLE */}
        {activeTab === 'facts' && (
          <div className="facts-container">
            <table className="evidence-table">
              <thead>
                <tr>
                  <th>Fact ID</th>
                  <th>Fact Type</th>
                  <th>Value</th>
                  <th>Confidence</th>
                  <th>Source Location</th>
                </tr>
              </thead>
              <tbody>
                {evidence_facts.map((fact) => (
                  <tr
                    key={fact.evidence_fact_id}
                    className={selectedFact?.evidence_fact_id === fact.evidence_fact_id ? 'selected-row' : ''}
                    onClick={() => setSelectedFact(fact)}
                  >
                    <td><code>{fact.evidence_fact_id}</code></td>
                    <td><span className="fact-type-tag">{fact.fact_type}</span></td>
                    <td className="fact-val-col">
                      {typeof fact.value === 'number'
                        ? fact.value.toLocaleString('vi-VN') + (fact.currency ? ` ${fact.currency}` : '')
                        : String(fact.value)}
                    </td>
                    <td>
                      <span className="conf-badge">{(fact.confidence * 100).toFixed(0)}%</span>
                    </td>
                    <td className="source-col">
                      Trang {fact.source?.page} • <em>"{fact.source?.text}"</em>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {selectedFact && (
              <div className="fact-detail-popover">
                <h4>
                  <Search size={14} /> Source Provenance Detail — {selectedFact.evidence_fact_id}
                </h4>
                <p><strong>Fact:</strong> {selectedFact.fact_type} = {String(selectedFact.value)}</p>
                <p><strong>Document Page:</strong> Trang {selectedFact.source?.page}</p>
                <p><strong>Source Text Snippet:</strong></p>
                <blockquote className="source-quote">"{selectedFact.source?.text}"</blockquote>
                <p><strong>Bounding Box Coordinates:</strong> [{selectedFact.source?.bbox?.join(', ')}]</p>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: ECONOMIC MEANING */}
        {activeTab === 'economic' && (
          <div className="economic-grid">
            {economic_artifacts.map((art, idx) => (
              <div key={idx} className="economic-card">
                <div className="card-badge-status">{art.status}</div>
                <h3>Artifact Type: {art.artifact_type}</h3>
                <div className="econ-details">
                  <p><strong>Economic Object:</strong> <span className="highlight-tag">{art.economic_meaning?.economic_object}</span></p>
                  <p><strong>Obligation / Meaning:</strong> {art.economic_meaning?.obligation_type || 'N/A'}</p>
                  <p><strong>Amount:</strong> {art.economic_meaning?.amount ? art.economic_meaning.amount.toLocaleString('vi-VN') + ' VND' : 'N/A'}</p>
                  <p><strong>Issue Date:</strong> {art.economic_meaning?.issue_date || 'N/A'}</p>
                  <p><strong>Due Date:</strong> {art.economic_meaning?.due_date || 'N/A'}</p>
                  <p><strong>Counterparty:</strong> {art.economic_meaning?.counterparty?.name || 'N/A'} ({art.economic_meaning?.counterparty?.role || 'N/A'})</p>
                </div>
                <div className="refs-group">
                  <span>Evidence References:</span>
                  {art.evidence_refs?.map((ref, rIdx) => (
                    <code key={rIdx}>{ref}</code>
                  ))}
                </div>
              </div>
            ))}

            <div className="economic-card bindings-card">
              <h3>Object Binding Candidates</h3>
              <ul className="binding-list">
                {object_bindings.map((b, idx) => (
                  <li key={idx}>
                    <span className="obj-type">{b.object_type}</span>
                    <ArrowRight size={14} />
                    <span className="candidate-name">{b.candidate_name}</span>
                    <span className="match-tag">{b.match_status}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* TAB 3: CASH FLOW IMPACT */}
        {activeTab === 'cashflow' && (
          <div className="cashflow-container">
            <div className="impact-card">
              <div className="impact-header">
                <TrendingUp size={22} color="var(--accent-indigo)" />
                <h3>Cashflow Relevance Analysis</h3>
              </div>
              <div className="impact-grid">
                <div className="impact-item">
                  <span className="impact-label">Relevance Level</span>
                  <span className="impact-val badge-high">{cashflow_relevance.relevance}</span>
                </div>
                <div className="impact-item">
                  <span className="impact-label">Direction</span>
                  <span className="impact-val">{cashflow_relevance.direction}</span>
                </div>
                <div className="impact-item">
                  <span className="impact-label">Cashflow Status</span>
                  <span className="impact-val status-badge">{cashflow_relevance.cashflow_status}</span>
                </div>
                <div className="impact-item">
                  <span className="impact-label">Basis</span>
                  <span className="impact-val">{cashflow_relevance.basis || 'N/A'}</span>
                </div>
                <div className="impact-item">
                  <span className="impact-label">Impact Amount</span>
                  <span className="impact-val amount-highlight">
                    {cashflow_relevance.amount ? cashflow_relevance.amount.toLocaleString('vi-VN') + ' VND' : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: FUNDING RELEVANCE */}
        {activeTab === 'funding' && (
          <div className="funding-container">
            <div className="impact-card">
              <div className="impact-header">
                <Award size={22} color="var(--accent-amber)" />
                <h3>Funding Input Eligibility</h3>
              </div>
              <p className="funding-disclaimer">
                <em>Lưu ý: Engine chỉ xác định vai trò bằng chứng (Evidence Role) của tài liệu cho downstream Funding logic. Không đưa ra quyết định duyệt giải ngân tự động.</em>
              </p>
              <div className="funding-section">
                <h4>Relevance: <span className="badge-high">{funding_relevance.relevance}</span></h4>
                <div className="roles-list">
                  <strong>Evidence Roles:</strong>
                  <div className="tag-group">
                    {funding_relevance.evidence_roles?.map((role, idx) => (
                      <span key={idx} className="role-tag">{role}</span>
                    ))}
                  </div>
                </div>

                <div className="reasons-list" style={{ marginTop: '12px' }}>
                  <strong>Reason Codes:</strong>
                  <div className="tag-group">
                    {funding_relevance.reason_codes?.map((code, idx) => (
                      <span key={idx} className="reason-tag">{code}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: GRAPH & LINEAGE */}
        {activeTab === 'graph' && (
          <div className="graph-container">
            <div className="lineage-box">
              <h4><ExternalLink size={16} /> Lineage & Provenance</h4>
              <p><strong>Lineage ID:</strong> <code>{lineage.lineage_id}</code></p>
              <p><strong>Parent Document ID:</strong> <code>{lineage.parent_document_id}</code></p>
              <p><strong>Extraction Method:</strong> {provenance.extraction_method} ({provenance.model?.provider})</p>
              <p><strong>Extracted At:</strong> {provenance.extracted_at}</p>
            </div>

            <div className="graph-box" style={{ marginTop: '16px' }}>
              <h4><Share2 size={16} /> Multi-Document Transaction Graph</h4>
              {document_relationships.length === 0 ? (
                <p className="empty-graph-text">Chưa có liên kết với tài liệu khác trong chuỗi giao dịch.</p>
              ) : (
                <div className="graph-edges">
                  {document_relationships.map((rel, idx) => (
                    <div key={idx} className="graph-edge-card">
                      <code>{rel.from}</code>
                      <div className="edge-rel">
                        <span>{rel.relationship}</span>
                        <ArrowRight size={14} />
                      </div>
                      <code>{rel.to}</code>
                      <span className="edge-conf">({(rel.confidence * 100).toFixed(0)}%)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
