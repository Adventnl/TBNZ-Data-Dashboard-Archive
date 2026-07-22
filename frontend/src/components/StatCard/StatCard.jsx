import { Card, Typography } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { useMemo, useState } from 'react';
import './StatCard.css';

const { Text, Title } = Typography;

export default function StatCard({
  title,
  value,
  prefix,
  suffix,
  change,
  changeLabel,
  icon,
  iconBg = '#FFF8E1',
  iconColor = '#FFCC00',
  toggleValue = false,
  fullValue,
  style,
}) {
  const [showFullValue, setShowFullValue] = useState(false);

  const isPositive = change > 0;
  const changeColor = change === 0 || change === undefined
    ? 'var(--color-text-tertiary)'
    : isPositive
      ? 'var(--color-success)'
      : 'var(--color-danger)';

  const displayValue = toggleValue && showFullValue ? (fullValue ?? value) : value;
  const displayText = `${prefix || ''}${displayValue ?? ''}${suffix || ''}`;

  const valueSizeClass = useMemo(() => {
    const textLength = String(displayText).length;
    if (textLength >= 20) return 'stat-card-value--xs';
    if (textLength >= 15) return 'stat-card-value--sm';
    return '';
  }, [displayText]);

  return (
    <Card className="stat-card" style={style} bodyStyle={{ padding: '20px 24px' }}>
      <div className="stat-card-inner">
        <div className="stat-card-content">
          <Text className="stat-card-title" type="secondary">{title}</Text>
          <div className="stat-card-value-row">
            <div className="stat-card-value-slot">
              {toggleValue ? (
                <button
                  type="button"
                  className="stat-card-value-toggle"
                  onClick={() => setShowFullValue((prev) => !prev)}
                  title={showFullValue ? '点击切换为简写' : '点击查看具体数字'}
                  aria-label={showFullValue ? '切换为简写数字' : '切换为完整数字'}
                >
                  <Title level={3} className={`stat-card-value ${valueSizeClass}`.trim()} style={{ margin: 0 }}>
                    {displayText}
                  </Title>
                </button>
              ) : (
                <Title level={3} className={`stat-card-value ${valueSizeClass}`.trim()} style={{ margin: 0 }}>
                  {displayText}
                </Title>
              )}
            </div>
            {change !== undefined && (
              <span className="stat-card-change" style={{ color: changeColor }}>
                {isPositive ? <ArrowUpOutlined /> : change < 0 ? <ArrowDownOutlined /> : null}
                {' '}{Math.abs(change)}%
              </span>
            )}
          </div>
          {changeLabel && (
            <Text type="secondary" className="stat-card-label">{changeLabel}</Text>
          )}
        </div>
        {icon && (
          <div
            className="stat-card-icon"
            style={{ background: iconBg, color: iconColor }}
          >
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}
