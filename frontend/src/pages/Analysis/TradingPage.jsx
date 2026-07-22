import { useEffect, useMemo, useState } from 'react';
import { Row, Col, Card, Select, Button, Typography, Table, Space, message, Spin, Empty } from 'antd';
import {
  DollarOutlined,
  RiseOutlined,
  SwapOutlined,
  ShoppingCartOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { PageHeader, StatCard } from '../../components';
import { tradingAPI } from '../../services/api';
import './TradingPage.css';

const { Text } = Typography;

const MARKET_OPTIONS = [
  { value: 'all', label: '全部市场 (All Markets)' },
  { value: 'NZ', label: 'NZ' },
  { value: 'US', label: 'US' },
  { value: 'AU', label: 'AU' },
  { value: 'HK', label: 'HK' },
];

const TRADE_TYPE_OPTIONS = [
  { value: 'all', label: '全部交易类型' },
  { value: 'stock', label: '股票' },
  { value: 'option', label: '期权' },
  { value: 'futures', label: '期货' },
  { value: 'fund', label: '基金' },
  { value: 'etf', label: 'ETF' },
];

function formatVolume(value, prefix = 'NZ$') {
  const amount = Number(value || 0);
  if (!Number.isFinite(amount)) {
    return `${prefix}0`;
  }
  if (Math.abs(amount) >= 1_000_000) {
    return `${prefix}${(amount / 1_000_000).toFixed(2)}M`;
  }
  if (Math.abs(amount) >= 1_000) {
    return `${prefix}${(amount / 1_000).toFixed(1)}K`;
  }
  return `${prefix}${amount.toFixed(0)}`;
}

function formatPercent(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric)) {
    return '0.0%';
  }
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(1)}%`;
}

export default function TradingPage() {
  const [period, setPeriod] = useState('30d');
  const [market, setMarket] = useState('all');
  const [tradeType, setTradeType] = useState('all');

  const [overview, setOverview] = useState({
    total_volume: { value: 0, usd_equiv: 0 },
    change_pct: 0,
    previous_volume: { value: 0, change_pct: 0 },
    pre_previous_volume: { value: 0 },
    aov: { value: 0, change_pct: 0 },
  });

  const [trendLoading, setTrendLoading] = useState(false);
  const [trendData, setTrendData] = useState({ current: [], previous: [] });

  const [categoryLoading, setCategoryLoading] = useState(false);
  const [categories, setCategories] = useState([]);

  const baseParams = useMemo(
    () => ({ period, market, trade_type: tradeType }),
    [period, market, tradeType]
  );

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        const data = await tradingAPI.getOverview(baseParams);
        setOverview(data);
      } catch (error) {
        message.error(`加载交易概览失败: ${error.message}`);
      }
    };

    const fetchTrends = async () => {
      setTrendLoading(true);
      try {
        const data = await tradingAPI.getTrends(baseParams);
        setTrendData(data);
      } catch (error) {
        message.error(`加载交易趋势失败: ${error.message}`);
      } finally {
        setTrendLoading(false);
      }
    };

    const fetchCategories = async () => {
      setCategoryLoading(true);
      try {
        const data = await tradingAPI.getCategories(baseParams);
        setCategories(data || []);
      } catch (error) {
        message.error(`加载交易品类失败: ${error.message}`);
      } finally {
        setCategoryLoading(false);
      }
    };

    fetchOverview();
    fetchTrends();
    fetchCategories();
  }, [baseParams]);

  const trendOption = useMemo(() => {
    const labels = (trendData.current || []).map((item) => item.date);
    const currentValues = (trendData.current || []).map((item) => Number(item.value || 0));
    const previousValues = (trendData.previous || []).map((item) => Number(item.value || 0));

    return {
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#333',
        textStyle: { color: '#fff', fontSize: 12 },
        formatter: (params) => {
          let result = `${params[0]?.axisValue || ''}<br/>`;
          params.forEach((p) => {
            result += `${p.marker} ${p.seriesName}: NZ$${Number(p.value || 0).toLocaleString()}<br/>`;
          });
          return result;
        },
      },
      legend: {
        top: 10,
        right: 20,
        data: ['本期 (Current)', '上期 (Previous)'],
        itemWidth: 12,
        itemHeight: 12,
        textStyle: { fontSize: 12, color: '#666' },
      },
      grid: { left: 50, right: 20, top: 50, bottom: 30 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: '#E8E8E8' } },
        axisLabel: { color: '#999' },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#F0F0F0' } },
        axisLabel: {
          color: '#999',
          formatter: (v) => (Number(v) / 1000).toFixed(0) + 'k',
        },
      },
      series: [
        {
          name: '本期 (Current)',
          type: 'line',
          data: currentValues,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { color: '#FFCC00', width: 3 },
          itemStyle: { color: '#FFCC00' },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(255, 204, 0, 0.15)' },
                { offset: 1, color: 'rgba(255, 204, 0, 0)' },
              ],
            },
          },
        },
        {
          name: '上期 (Previous)',
          type: 'line',
          data: previousValues,
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { color: '#D9D9D9', width: 2, type: 'dashed' },
          itemStyle: { color: '#D9D9D9' },
        },
      ],
    };
  }, [trendData]);

  const categoryOption = useMemo(() => {
    const chartData = (categories || []).map((item, index) => {
      const colors = ['#FFCC00', '#52C41A', '#1890FF', '#FF8C00', '#722ED1', '#13C2C2'];
      return {
        value: Number(item.value || 0),
        name: item.name,
        itemStyle: { color: colors[index % colors.length] },
      };
    });

    return {
      tooltip: {
        trigger: 'item',
        formatter: (params) => `${params.name}: ${Number(params.percent || 0).toFixed(1)}%`,
      },
      legend: { show: false },
      series: [
        {
          type: 'pie',
          radius: ['50%', '75%'],
          center: ['50%', '50%'],
          label: {
            show: true,
            position: 'outside',
            formatter: '{b}\n{d}%',
            fontSize: 11,
          },
          data: chartData,
        },
      ],
      graphic: [
        {
          type: 'text',
          left: 'center',
          top: 'center',
          style: {
            text: `Total\n${categories.length ? '100%' : '0%'}`,
            textAlign: 'center',
            fontSize: 14,
            fontWeight: 600,
            fill: '#333',
          },
        },
      ],
    };
  }, [categories]);

  return (
    <div className="trading-page">
      <PageHeader
        title="本月交易额详细分析"
        breadcrumb={['综合分析', '本月交易额']}
        extra={
          <Space>
            <Select
              value={market}
              size="small"
              style={{ width: 170 }}
              options={MARKET_OPTIONS}
              onChange={(value) => {
                setMarket(value);
              }}
            />
            <Select
              value={tradeType}
              size="small"
              style={{ width: 150 }}
              options={TRADE_TYPE_OPTIONS}
              onChange={(value) => {
                setTradeType(value);
              }}
            />
            <Button.Group size="small">
              <Button type={period === '7d' ? 'primary' : 'default'} onClick={() => setPeriod('7d')}>7D</Button>
              <Button
                type={period === '30d' ? 'primary' : 'default'}
                onClick={() => setPeriod('30d')}
                style={period === '30d' ? { background: '#333', borderColor: '#333' } : {}}
              >
                30D
              </Button>
              <Button type={period === '1y' ? 'primary' : 'default'} onClick={() => setPeriod('1y')}>1Y</Button>
            </Button.Group>
          </Space>
        }
      />

      {/* Stat Cards */}
      <Row gutter={16} wrap={false} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <StatCard
            title="总交易额"
            value={formatVolume(overview.total_volume?.value)}
            changeLabel={`≈ $${Number(overview.total_volume?.usd_equiv || 0).toLocaleString()} USD`}
            icon={<DollarOutlined />}
            iconBg="#FFF3B0"
            iconColor="#E6B800"
          />
        </Col>
        <Col span={6}>
          <StatCard
            title="环比变化"
            value={formatPercent(overview.change_pct)}
            changeLabel={`对比上期 ${formatVolume(overview.previous_volume?.value)}`}
            icon={<RiseOutlined />}
            iconBg="#E8F5E9"
            iconColor="#52C41A"
          />
        </Col>
        <Col span={6}>
          <StatCard
            title="上期交易量"
            value={formatVolume(overview.previous_volume?.value)}
            changeLabel={`上期环比 ${formatPercent(overview.previous_volume?.change_pct)}`}
            icon={<SwapOutlined />}
            iconBg="#E3F2FD"
            iconColor="#1890FF"
          />
        </Col>
        <Col span={6}>
          <StatCard
            title="平均订单金额 (AOV)"
            value={formatVolume(overview.aov?.value)}
            change={Number(overview.aov?.change_pct || 0)}
            icon={<ShoppingCartOutlined />}
            iconBg="#F3E5F5"
            iconColor="#9C27B0"
          />
        </Col>
      </Row>

      {/* Trading Trends Chart */}
      <Card
        title="交易趋势分析 (Trading Trends)"
        className="chart-card"
        style={{ marginBottom: 24 }}
        bodyStyle={{ padding: '12px 16px' }}
      >
        {trendLoading ? (
          <div className="chart-loading-wrap">
            <Spin size="large" />
          </div>
        ) : (trendData.current || []).length > 0 ? (
          <ReactECharts option={trendOption} style={{ height: 320 }} />
        ) : (
          <div className="chart-loading-wrap">
            <Empty description="暂无趋势数据" />
          </div>
        )}
      </Card>

      {/* Bottom Row: Category Distribution */}
      <Row gutter={16} wrap={false}>
        <Col span={24}>
          <Card title="交易品类分布 (Category)" className="chart-card" bodyStyle={{ padding: '12px' }}>
            {categoryLoading ? (
              <div className="chart-loading-wrap">
                <Spin />
              </div>
            ) : categories.length > 0 ? (
              <ReactECharts option={categoryOption} style={{ height: 280 }} />
            ) : (
              <div className="chart-loading-wrap">
                <Empty description="暂无品类数据" />
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
