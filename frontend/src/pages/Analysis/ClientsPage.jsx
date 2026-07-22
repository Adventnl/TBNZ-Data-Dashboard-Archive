
import { Row, Col, Card, Space, Button, Typography } from 'antd';
import {
  ArrowRightOutlined,
  UnorderedListOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { PageHeader, StatCard, SignalCard } from '../../components';
import './ClientsPage.css';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;


// Mock data for signal cards
const signalData = [
  {
    name: '张立伟 (Liwei)',
    uid: '98234123',
    tags: ['HNW'],
    signalType: 'urgent',
    signalTitle: '大额出金提醒 (3笔, 共计$50k+)',
    signalDescription:
      '本期检测到 3 笔异常，累计出金 NZ$75k+，较上周 +150k，近期调整了美股科技股的仓位，并且对稳健型超额资产表现出兴趣，流失风险较高。',
    urgent: true,
  },
  {
    name: '王晓芳 (Xiaofang)',
    uid: '82741920',
    tags: ['Inactive'],
    signalType: 'warning',
    signalTitle: '活跃度大幅下降',
    signalDescription:
      '连续 2 周未登入，过去平均每周交易 4 次 (NZ$15k vol/week)',
    urgent: false,
  },
  {
    name: '李明 (Ming)',
    uid: '34120932',
    tags: ['Frequent Trader'],
    signalType: 'warning',
    signalTitle: '高频交易异常',
    signalDescription: '期权交易量突增 (Volume Spike 3x Avg)，涉及多只美股杠杆 ETF',
    urgent: false,
  },
  {
    name: '周杰 (Jay)',
    uid: '19827364',
    tags: ['New'],
    signalType: 'info',
    signalTitle: '首次大额入金',
    signalDescription: '开户后 3 天内单笔存入 NZ$120k，尚未进行任何交易动作',
    urgent: false,
  },
  {
    name: '陈思远 (Siyuan)',
    uid: '52148930',
    tags: ['HNW'],
    signalType: 'success',
    signalTitle: '大额入金 ($100k+)',
    signalDescription: '新西兰本金客户',
    urgent: true,
  }
];

// Mini chart config for stat cards
const miniBarOption = {
  grid: { left: 0, right: 0, top: 0, bottom: 0 },
  xAxis: {
    show: false,
    type: 'category',
    data: ['1', '2', '3', '4', '5', '6', '7', '8'],
  },
  yAxis: {
    show: false,
    type: 'value',
  },
  series: [
    {
      type: 'bar',
      data: [
        { value: 28, itemStyle: { color: '#E5E7EB' } },
        { value: 42, itemStyle: { color: '#E5E7EB' } },
        { value: 55, itemStyle: { color: '#E5E7EB' } },
        { value: 50, itemStyle: { color: '#E5E7EB' } },
        { value: 68, itemStyle: { color: '#E5E7EB' } },
        { value: 72, itemStyle: { color: '#E5E7EB' } },
        { value: 86, itemStyle: { color: '#E5E7EB' } },
        { value: 98, itemStyle: { color: '#22C55E' } },
      ],
      barWidth: 14,
      barGap: '35%',
      itemStyle: {
        borderRadius: [8, 8, 0, 0],
      },
    },
  ],
};

const miniLineOption = {
  grid: { left: 0, right: 0, top: 6, bottom: 0 },
  xAxis: {
    show: false,
    type: 'category',
    data: ['1', '2', '3', '4', '5', '6', '7', '8'],
  },
  yAxis: {
    show: false,
    type: 'value',
    min: 340,
    max: 420,
  },
  series: [
    {
      type: 'line',
      data: [350, 400, 350, 420, 350, 410, 360, 410],
      smooth: true,
      smoothMonotone: 'x',
      symbol: 'none',
      lineStyle: {
        color: '#9CA3AF',
        width: 3,
      },
    },
  ],
};

const miniRankBarOption = {
  grid: { left: 0, right: 0, top: 0, bottom: 0 },
  xAxis: {
    show: false,
    type: 'category',
    data: ['1', '2', '3', '4', '5', '6', '7', '8'],
  },
  yAxis: {
    show: false,
    type: 'value',
  },
  series: [
    {
      type: 'bar',
      data: [
        { value: 20, itemStyle: { color: '#E5E7EB' } },
        { value: 26, itemStyle: { color: '#E5E7EB' } },
        { value: 34, itemStyle: { color: '#E5E7EB' } },
        { value: 40, itemStyle: { color: '#E5E7EB' } },
        { value: 52, itemStyle: { color: '#E5E7EB' } },
        { value: 61, itemStyle: { color: '#E5E7EB' } },
        { value: 73, itemStyle: { color: '#E5E7EB' } },
        { value: 88, itemStyle: { color: '#A855F7' } },
      ],
      barWidth: 14,
      itemStyle: {
        borderRadius: [8, 8, 0, 0],
      },
    },
  ],
};

export default function ClientsPage() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState('table');
  const [market, setMarket] = useState('all');
  const [clientType, setClientType] = useState('all');
  const [signalType, setSignalType] = useState('all');
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overview, setOverview] = useState({
    trading_volume: { value: 0, currency: 'NZD', change_pct: 0 },
    auc: { value: 0, currency: 'USD', change_pct: 0 },
    ranking: { value: 0, total: 100, change: 0 },
  });

  const [signalsLoading, setSignalsLoading] = useState(false);
  const [signals, setSignals] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 6, total: 0 });

  const [detailVisible, setDetailVisible] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailData, setDetailData] = useState(null);
  const [pushingUid, setPushingUid] = useState('');

  const fetchOverview = async (selectedMarket) => {
    setOverviewLoading(true);
    try {
      const data = await clientsAPI.getOverview({ market: selectedMarket });
      setOverview(data);
    } catch (error) {
      message.error(`加载客户概览失败: ${error.message}`);
    } finally {
      setOverviewLoading(false);
    }
  };

  const fetchSignals = async ({ page, pageSize, selectedSignalType, selectedClientType, selectedMarket }) => {
    setSignalsLoading(true);
    try {
      const data = await clientsAPI.getSignals({
        page,
        page_size: pageSize,
        signal_type: selectedSignalType,
        client_type: selectedClientType,
        market: selectedMarket,
      });
      setSignals(data.items || []);
      setPagination({
        page: data.page || page,
        pageSize: data.page_size || pageSize,
        total: data.total || 0,
      });
    } catch (error) {
      message.error(`加载客户信号失败: ${error.message}`);
    } finally {
      setSignalsLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview(market);
  }, [market]);

  useEffect(() => {
    fetchSignals({
      page: pagination.page,
      pageSize: pagination.pageSize,
      selectedSignalType: signalType,
      selectedClientType: clientType,
      selectedMarket: market,
    });
  }, [signalType, clientType, market, pagination.page, pagination.pageSize]);

  const onFilterChange = (setter, value) => {
    setter(value);
    setPagination((prev) => ({ ...prev, page: 1 }));
  };

  const openDetail = async (uid) => {
    setDetailVisible(true);
    setDetailLoading(true);
    try {
      const data = await clientsAPI.getDetail(uid);
      setDetailData(data);
    } catch (error) {
      message.error(`加载客户详情失败: ${error.message}`);
      setDetailVisible(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const pushToSales = async (signal) => {
    setPushingUid(signal.uid);
    try {
      await clientsAPI.pushToSales(signal.uid, {
        signal_type: signal.signal_type,
        note: signal.signal_title,
        operator: 'admin',
      });
      message.success(`已将 ${signal.name} 推送给 Sales`);
      await fetchSignals({
        page: pagination.page,
        pageSize: pagination.pageSize,
        selectedSignalType: signalType,
        selectedClientType: clientType,
        selectedMarket: market,
      });
    } catch (error) {
      message.error(`推送失败: ${error.message}`);
    } finally {
      setPushingUid('');
    }
  };

  const rankingValue = overview.ranking?.value > 0 ? `Top ${overview.ranking.value}` : 'N/A';

  return (
    <div className="clients-page">

      {/* Stat Cards Row */}
      <Row gutter={16} className="stat-cards-row">
        <Col span={8}>
          <Card className="overview-stat-card" bodyStyle={{ padding: '20px' }}>
            <div className="overview-stat-header">
              <Text type="secondary">本月交易额 (Trading Volume)</Text>
                <img
                  src="/right-arrow.png"
                  alt="arrow"
                  className="arrow-img"
                  onClick={() => navigate('/analysis/trading')}
                />
            </div>
            <div className="overview-stat-value">
              <span className="big-value">NZ$12.5M</span>
              <span className="change-badge positive">↑ 15.2%</span>
            </div>
            <ReactECharts option={miniBarOption} style={{ height: 48, marginTop: 8 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card className="overview-stat-card" bodyStyle={{ padding: '20px' }}>
            <div className="overview-stat-header">
              <Text type="secondary">资产托管 (AUC)</Text>
                <img
                  src="/right-arrow.png"
                  alt="arrow"
                  className="arrow-img"
                  onClick={() => navigate('/analysis/auc')}
                />
            </div>
            <div className="overview-stat-value">
              <span className="big-value">NZ$380M</span>
              <span className="change-badge neutral">↓ 0.5%</span>
            </div>
            <ReactECharts option={miniLineOption} style={{ height: 48, marginTop: 8 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card className="overview-stat-card" bodyStyle={{ padding: '20px' }}>
            <div className="overview-stat-header">
              <Text type="secondary">排名变化 (NZ Top 100)</Text>
                <img
                  src="/right-arrow.png"
                  alt="arrow"
                  className="arrow-img"
                  onClick={() => navigate('/analysis/rankings')}
                />
            </div>
            <div className="overview-stat-value">
              <span className="big-value">Top 12</span>
              <span className="change-badge positive">↑ +8</span>
            </div>
              <ReactECharts option={miniRankBarOption} style={{ height: 48, marginTop: 8 }} />
          </Card>
        </Col>
      </Row>





      {/* Client Signal List */}
      <Card className="signal-list-card" bodyStyle={{ padding: 0 }} >
        <div className="signal-list-header">
          <div className="signal-list-header-left">
            <Text strong style={{ fontSize: 16 }}>待处理客户列表</Text>
            <Space>
              <Button type={undefined} className="filter-btn active">全部</Button>
              <Button type={undefined} className="filter-btn">交易量激增</Button>
              <Button type={undefined} className="filter-btn">大额入金</Button>
              <Button type={undefined} className="filter-btn">大额出金</Button>
              <Button type={undefined} className="filter-btn">沉睡客户</Button>
            </Space>
          </div>

          <div className="view-toggle">
            <button
              className={`view-toggle-btn ${viewMode === 'table' ? 'active' : ''}`}
              onClick={() => setViewMode('table')}
            >
              <UnorderedListOutlined />
            </button>

            <button
              className={`view-toggle-btn ${viewMode === 'card' ? 'active' : ''}`}
              onClick={() => setViewMode('card')}
            >
              <AppstoreOutlined />
            </button>
          </div>
        </div>

        
       {viewMode === 'table' && (
        <div className="signal-table-header">
          <div className="col col-detail">客户信息</div>
          <div className="col col-tag">标签</div>
          <div className="col col-signal">异动原因</div>
          <div className="col col-action">操作</div>
        </div>
        )}

        <div className={`signal-list-body ${viewMode === 'card' ? 'card-mode' : ''}`}>
          {signalData.map((signal, index) => (
            <SignalCard
              key={index}
              {...signal}
              viewMode={viewMode}
              onAction={() => navigate(`/analysis/clientDetail/${signal.uid}`)}
            />
          ))}
        </div>
      </Card>
    </div>
  );
}
