import { Typography, Button, Avatar, Space } from 'antd';
import { RightOutlined } from '@ant-design/icons';
import ClientTag from '../ClientTag/ClientTag';
import './SignalCard.css';

const { Text } = Typography;

const signalColors = {
  urgent: '#FF4D4F',
  warning: '#FF8C00',
  info: '#1890FF',
  success: '#52C41A',
};

export default function SignalCard({
  name,
  uid,
  tags = [],
  signalType = 'warning',
  signalTitle,
  signalDescription,
  actionLabel = '查看详情',
  onAction,
  urgent = false,
  viewMode = 'table',
}) {
  const initial = name ? name.charAt(0) : '?';
  const signalColor = signalColors[signalType] || '#FF8C00';

  if (viewMode === 'card') {
    return (
      <div className="signal-grid-card" onClick={onAction}>
        <div className="signal-grid-top">
          <div className="signal-grid-user">
            <Avatar size={44} className="signal-grid-avatar">
              {initial}
            </Avatar>

            <div className="signal-grid-user-info">
              <Text strong className="signal-grid-name">
                {name}
              </Text>
              <Text type="secondary" className="signal-grid-uid">
                UID: {uid}
              </Text>
            </div>
          </div>

          <RightOutlined className="signal-grid-arrow" />
        </div>

        <div className="signal-grid-tags">
          <Space size={6} wrap>
            {tags.map((tag) => (
              <ClientTag key={tag} type={tag} />
            ))}
          </Space>
        </div>

        <div className="signal-grid-signal-box">
          <div className="signal-grid-signal-title">
            <span
              className="signal-dot"
              style={{ background: signalColor }}
            />
            <Text strong style={{ color: signalColor }}>
              {signalTitle}
            </Text>
          </div>

          <Text type="secondary" className="signal-grid-signal-desc">
            {signalDescription}
          </Text>
        </div>
      </div>
    );
  }

  return (
    <div className="signal-row">
      <div className="col col-detail">
        <Avatar size={44}>{initial}</Avatar>
        <div className="user-info">
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            UID: {uid}
          </Text>
        </div>
      </div>

      <div className="col col-tag">
        <Space size={4}>
          {tags.map((tag) => (
            <ClientTag key={tag} type={tag} />
          ))}
        </Space>
      </div>

      <div className="col col-signal">
        <div className="signal-line">
          <span
            className="signal-dot"
            style={{ background: signalColor }}
          />
          <Text strong style={{ color: signalColor }}>
            {signalTitle}
          </Text>
        </div>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {signalDescription}
        </Text>
      </div>

      <div className="col col-action">
        <Button
          className="follow-btn"
          
          onClick={onAction}
        >
          立即跟进
        </Button>
      </div>
    </div>
  );
}