import { useState } from 'react';
import { Row, Col, Card, Table, Select, Button, Typography, Tag, Space, Avatar, Input } from 'antd';
import {
  SearchOutlined,
  ExportOutlined,
  FilterOutlined,
  CalendarOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { PageHeader, StatCard } from '../../components';
import './ActivitiesPage.css';

const { Text, Title } = Typography;

// Activity list
const activities = [
  {
    id: 1,
    name: '社区博览会 2024',
    date: '2024-01-10',
    location: '奥克兰中心城区',
    status: '进行中',
    visitors: 12480,
    signups: 856,
    conversion: 6.86,
  },
  {
    id: 2,
    name: '科技圆桌派',
    date: '2023-12-15',
    location: '全国线上',
    status: '已完成',
    visitors: 8920,
    signups: 412,
    conversion: 4.62,
  },
  {
    id: 3,
    name: '奥克兰大学合影周',
    date: '2023-11-22',
    location: 'Auckland University',
    status: '已完成',
    visitors: 5640,
    signups: 289,
    conversion: 5.12,
  },
];

// Execution trend chart
const trendOption = {
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' },
  },
  legend: {
    top: 5,
    right: 20,
    data: ['累计访客量 (L)', '新注册人数 (R)'],
    textStyle: { fontSize: 11 },
  },
  grid: { left: 50, right: 50, top: 40, bottom: 25 },
  xAxis: {
    type: 'category',
    data: ['Day 1 (2-10)', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6 (01-15)'],
    axisLine: { lineStyle: { color: '#E8E8E8' } },
    axisLabel: { color: '#999', fontSize: 10 },
  },
  yAxis: [
    {
      type: 'value',
      name: '累计访客',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#F0F0F0' } },
      axisLabel: { color: '#999' },
    },
    {
      type: 'value',
      name: '新注册',
      axisLine: { show: false },
      splitLine: { show: false },
      axisLabel: { color: '#999' },
    },
  ],
  series: [
    {
      name: '累计访客量 (L)',
      type: 'line',
      data: [2100, 4500, 6800, 8900, 10800, 12480],
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#FFCC00', width: 3 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(255, 204, 0, 0.2)' },
            { offset: 1, color: 'rgba(255, 204, 0, 0)' },
          ],
        },
      },
    },
    {
      name: '新注册人数 (R)',
      type: 'line',
      yAxisIndex: 1,
      data: [120, 180, 160, 150, 130, 116],
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#FF8C00', width: 2 },
      itemStyle: { color: '#FF8C00' },
    },
  ],
};

// Tracking table data
const trackingData = [
  { seq: '0.1', channel: '(0429)', inviteCode: '李 + (E)', source: '2024\n(06-10)', type: '注册', amount: '$90', status: '已入金', result: '匹配完成', statusIcon: '✅' },
  { seq: '0.7', channel: '(0725)', inviteCode: '上飞船\n联合', source: '2873-4\n(02-15)', type: '注册', amount: '$300', status: '待入金', result: '尤名记', statusIcon: '⏳' },
  { seq: '0.9', channel: '(1106)', inviteCode: '', source: '', type: '', amount: '$78', status: '已入金', result: '', statusIcon: '✅' },
];

const trackingColumns = [
  { title: '序', dataIndex: 'seq', key: 'seq', width: 40 },
  { title: '渠道', dataIndex: 'channel', key: 'channel', width: 80 },
  { title: '来源', dataIndex: 'inviteCode', key: 'inviteCode', width: 80 },
  { title: '注册日', dataIndex: 'source', key: 'source', width: 80 },
  { title: '入金额', dataIndex: 'amount', key: 'amount', width: 70 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 70,
    render: (v) => <Tag color={v === '已入金' ? 'green' : 'orange'}>{v}</Tag>
  },
  { title: '归因', dataIndex: 'result', key: 'result', width: 80 },
];

export default function ActivitiesPage() {
  const [selectedActivity, setSelectedActivity] = useState(activities[0]);

  return (
    <div className="activities-page">


      <Row gutter={16}>
        {/* Left: Activity Timeline */}
        <Col span={6}>
          <div className="activity-timeline">
            {activities.map((activity) => (
              <div
                key={activity.id}
                className={`activity-timeline-item ${selectedActivity.id === activity.id ? 'active' : ''}`}
                onClick={() => setSelectedActivity(activity)}
              >
                <div className="timeline-status">
                  <Tag
                    color={activity.status === '进行中' ? 'gold' : 'default'}
                    style={{ fontSize: 11 }}
                  >
                    {activity.status}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 11 }}>{activity.date}</Text>
                </div>
                <Text strong style={{ fontSize: 14 }}>{activity.name}</Text>
                <div className="timeline-location">
                  <EnvironmentOutlined style={{ fontSize: 11, color: '#999' }} />
                  <Text type="secondary" style={{ fontSize: 11 }}>{activity.location}</Text>
                </div>
              </div>
            ))}
          </div>
        </Col>

        {/* Right: Activity Detail */}
        <Col span={18}>
          {/* Activity Header */}
          <Card className="activity-detail-card" bodyStyle={{ padding: '20px 24px' }}>
            <div className="activity-detail-header">
              <div>
                <Title level={4} style={{ margin: 0 }}>{selectedActivity.name}</Title>
                <Text type="secondary">
                  针对本地社区华人群体和新移民用户 | 市场博览 & 互动体验 & 开户激励
                </Text>
              </div>
              <Tag color="processing">Print Status</Tag>
            </div>

            {/* Stat Cards */}
            <Row gutter={16} style={{ marginTop: 20 }}>
              <Col span={8}>
                <div className="activity-stat">
                  <Text type="secondary">活动总访客</Text>
                  <div className="activity-stat-value">
                    <Title level={3} style={{ margin: 0 }}>{selectedActivity.visitors.toLocaleString()}</Title>
                    <span className="change-badge positive">+8.4%</span>
                  </div>
                </div>
              </Col>
              <Col span={8}>
                <div className="activity-stat">
                  <Text type="secondary">新注册人数</Text>
                  <div className="activity-stat-value">
                    <Title level={3} style={{ margin: 0 }}>{selectedActivity.signups}</Title>
                    <span className="change-badge positive">+12.1%</span>
                  </div>
                </div>
              </Col>
              <Col span={8}>
                <div className="activity-stat">
                  <Text type="secondary">转化率</Text>
                  <div className="activity-stat-value">
                    <Title level={3} style={{ margin: 0 }}>{selectedActivity.conversion}%</Title>
                    <span className="change-badge positive">+1.5%</span>
                  </div>
                </div>
              </Col>
            </Row>
          </Card>

          {/* Execution Trend */}
          <Card
            className="chart-card"
            style={{ marginTop: 16 }}
            bodyStyle={{ padding: '12px 16px' }}
          >
            <Text strong style={{ fontSize: 15 }}>(Execution Trend)</Text>
            <ReactECharts option={trendOption} style={{ height: 240, marginTop: 8 }} />
          </Card>

          {/* Tracking Table */}
          <Card
            className="tracking-card"
            style={{ marginTop: 16 }}
            bodyStyle={{ padding: 0 }}
          >
            <div className="tracking-header">
              <Text strong style={{ fontSize: 15 }}>活动获客入金分析</Text>
              <Space>
                <Input size="small" placeholder="搜索..." prefix={<SearchOutlined />} style={{ width: 160 }} />
                <Button size="small" icon={<FilterOutlined />}>筛选</Button>
                <Button size="small" icon={<ExportOutlined />}>导出</Button>
              </Space>
            </div>
            <Table
              dataSource={trackingData}
              columns={trackingColumns}
              rowKey="seq"
              size="small"
              pagination={false}
              scroll={{ y: 200 }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
