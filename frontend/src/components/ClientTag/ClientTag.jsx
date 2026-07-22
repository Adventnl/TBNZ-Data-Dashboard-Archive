import { Tag } from 'antd';

const tagConfig = {
  HNW: { color: '#FFF8E1', textColor: '#B8860B', border: '#FFCC00' },
  'S-Class': { color: '#F9F0FF', textColor: '#722ED1', border: '#722ED1' },
  Inactive: { color: '#F5F5F5', textColor: '#999999', border: '#D9D9D9' },
  'Frequent Trader': { color: '#E6F7FF', textColor: '#1890FF', border: '#1890FF' },
  New: { color: '#F6FFED', textColor: '#52C41A', border: '#52C41A' },
};

export default function ClientTag({ type }) {
  const config = tagConfig[type] || { color: '#F5F5F5', textColor: '#666', border: '#D9D9D9' };

  return (
    <Tag
      style={{
        background: config.color,
        color: config.textColor,
        border: `1px solid ${config.border}`,
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 500,
      }}
    >
      [{type}]
    </Tag>
  );
}
