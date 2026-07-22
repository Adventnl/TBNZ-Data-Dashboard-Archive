import { Typography, Breadcrumb } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import './PageHeader.css';

const { Title, Text } = Typography;

export default function PageHeader({ title, subtitle, breadcrumb, extra }) {
  return (
    
    <div className="page-header">
      <div className="page-header-left">
        {breadcrumb && (
          <Breadcrumb
            className="page-breadcrumb"
            items={breadcrumb.map((item) => ({ title: item }))}
          />
        )}
        <Title level={4} className="page-title">{title}</Title>
        {subtitle && <Text type="secondary">{subtitle}</Text>}
      </div>
    </div>
  );
}
