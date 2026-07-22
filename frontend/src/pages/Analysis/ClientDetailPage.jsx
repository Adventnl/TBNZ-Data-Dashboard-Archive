import React, { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import './ClientDetailPage.css';

const mockClients = {
  '98234123': {
    id: '98234123',
    nameCn: '张立伟',
    nameEn: 'Zhang Liwei',
    avatar:
      'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80',
    tags: ['高净值客户', '新晋潜力客户', '长期持有'],
    auc: '$1,245,000',
    status: '待跟进',
    tradingPref: '美股、标普500 ETF',
    frequency: '偶尔交易',
    lastLogin: '2天前',
    email: 'liwei.zhang@example.com',
    phone: '+65 8823 4123',
    city: 'New Zealand, Auckland',
  },
  '82741920': {
    id: '82741920',
    nameCn: '王晓芳',
    nameEn: 'Xiaofang',
    avatar:
      'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80',
    tags: ['Inactive'],
    auc: '$384,000',
    status: '待唤醒',
    tradingPref: '港股、低频',
    frequency: '近两周未交易',
    lastLogin: '14天前',
    email: 'xiaofang.wang@example.com',
    phone: '+64 021 888 123',
    city: 'Auckland, New Zealand',
  },
};

const initialNotes = {
  '98234123': [
    {
      id: 1,
      author: 'Sarah Chen',
      role: '客户经理',
      time: '10月24日 · 14:30',
      type: 'staff',
      pinned: true,
      content:
        '讨论了第四季度的 market outlook 以及固定收益产品的多元化。客户表现出中度兴趣。关键点：注意利率敏感度。',
    },
    {
      id: 2,
      author: '张立伟（客户反馈）',
      role: '外部意见',
      time: '10月22日 · 09:15',
      type: 'client',
      pinned: false,
      content:
        '收到你们的报告了，Sarah。下周三我有时间去新加坡参加你们的晚宴，请帮我预留位置。',
    },
    {
      id: 3,
      author: 'Alex Li',
      role: '风险分析师',
      time: '10月18日 · 11:20',
      type: 'staff',
      pinned: false,
      content:
        '内部反馈：建议在晚宴上与其沟通对冲策略，降低波动性风险。',
    },
  ],
  '82741920': [
    {
      id: 1,
      author: 'Emily Wu',
      role: '客户经理',
      time: '10月21日 · 15:00',
      type: 'staff',
      pinned: false,
      content:
        '客户最近交易明显减少，建议先从简单问候开始，了解是否有新的资金安排。',
    },
  ],
};

export default function FollowUpPage() {
  const { clientId } = useParams();

  const client = useMemo(() => {
    return mockClients[clientId] || mockClients['98234123'];
  }, [clientId]);

  const [notes, setNotes] = useState(initialNotes[client.id] || []);
  const [newNote, setNewNote] = useState('');
  const [isPinned, setIsPinned] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredNotes = useMemo(() => {
    const keyword = searchTerm.trim().toLowerCase();
    if (!keyword) return notes;

    return notes.filter((note) => {
      return (
        note.author.toLowerCase().includes(keyword) ||
        note.role.toLowerCase().includes(keyword) ||
        note.content.toLowerCase().includes(keyword) ||
        note.time.toLowerCase().includes(keyword)
      );
    });
  }, [notes, searchTerm]);

  const handleSubmit = () => {
    const content = newNote.trim();
    if (!content) return;

    const item = {
      id: Date.now(),
      author: '我',
      role: '客户经理',
      time: '刚刚',
      type: 'self',
      pinned: isPinned,
      content,
    };

    setNotes((prev) => [item, ...prev]);
    setNewNote('');
    setIsPinned(false);
  };

  return (
    <div className="followup-page">
      <div className="followup-layout">
        {/* 左边客户信息 */}
        <aside className="client-info-card">
          <div className="client-avatar-wrap">
            <img src={client.avatar} alt={client.nameEn} className="client-avatar" />
          </div>

          <div className="client-name-cn">
            {client.nameCn} <span>({client.nameEn})</span>
          </div>
          <div className="client-id">UID: {client.id}</div>

          <div className="client-tags">
            {client.tags.map((tag) => (
              <span key={tag} className="client-tag">
                {tag}
              </span>
            ))}
          </div>

          <div className="client-section">
            <div className="info-grid">
              <div className="info-item">
                <div className="info-label">资产总额 (AUC)</div>
                <div className="info-value">{client.auc}</div>
              </div>

              <div className="info-item">
                <div className="info-label">当前状态</div>
                <div className="info-value">{client.status}</div>
              </div>

              <div className="info-item">
                <div className="info-label">交易偏好</div>
                <div className="info-value">{client.tradingPref}</div>
              </div>

              <div className="info-item">
                <div className="info-label">交易习惯</div>
                <div className="info-value">{client.frequency}</div>
              </div>

              <div className="info-item">
                <div className="info-label">最近行为</div>
                <div className="info-value">{client.lastLogin}</div>
              </div>
            </div>
          </div>

          <div className="client-section contact-section">


              <div className="contact-item">
                <img src="/email.png" className="contact-icon" />
                <span>{client.email}</span>
              </div>

              <div className="contact-item">
                <img src="/phone.png" className="contact-icon" />
                <span>{client.phone}</span>
              </div>

              <div className="contact-item">
                <img src="/location.png" className="contact-icon" />
                <span>{client.city}</span>
              </div>

          </div>
        </aside>

        {/* 右边 */}
        <section className="followup-main">
          {/* 上面留言记录 */}
          <div className="notes-card">
            <div className="card-header">
              <div className="card-title">跟进记录</div>

              <div className="notes-search">
                <input
                  type="text"
                  placeholder="搜索记录"
                  className="notes-search-input"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>

            <div className="notes-list">
              {filteredNotes.length > 0 ? (
                filteredNotes.map((note) => (
                  <div key={note.id} className="note-item">
                    <div className={`note-avatar note-avatar-${note.type}`}>
                      {note.author.slice(0, 1)}
                    </div>

                    <div className="note-content-wrap">
                      <div className="note-meta">
                        <span className="note-author">{note.author}</span>
                        <span className="note-role">{note.role}</span>
                        <span className="note-time">{note.time}</span>
                      </div>

                      <div className={`note-bubble note-bubble-${note.type}`}>
                        {note.content}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-notes">没有匹配到相关记录</div>
              )}
            </div>
          </div>

          {/* 下面编辑区 */}
          <div className="editor-card">
            <div className="card-header small">
              <div className="card-title">发布进度</div>
            </div>

            <div className="editor-box">
              <textarea
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="在此输入跟进详情、团队反馈或客户回复摘要..."
              />
            </div>

            <div className="editor-footer">
              <div className="editor-actions-left">
                <button type="button" className="mini-btn">
                  📎 附件
                </button>
              </div>

              <div className="editor-actions-right">
                <label className="checkbox-line">
                  <input
                    type="checkbox"
                    checked={isPinned}
                    onChange={(e) => setIsPinned(e.target.checked)}
                  />
                  <span>置顶</span>
                </label>

                <button type="button" className="save-btn" onClick={handleSubmit}>
                  记录
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}