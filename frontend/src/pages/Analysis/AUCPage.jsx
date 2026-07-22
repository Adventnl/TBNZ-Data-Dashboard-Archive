import { Row, Col, Card, Select, Typography, Space, Skeleton, Modal, Table, Tag, Button, Tabs } from 'antd';
import {
  BankOutlined,
  UserOutlined,
  SafetyOutlined,
  ArrowUpOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useState, useEffect, useMemo } from 'react';
import { PageHeader, StatCard } from '../../components';
// import { aucAPI } from '../../services/api';
import './AUCPage.css';

const { Text } = Typography;

const ALLOCATION_CHART_COLORS = ['#FFCC00', '#52C41A', '#1890FF', '#FF8C00', '#722ED1', '#13C2C2'];

const formatMonthLabel = (monthText) => {
  if (!monthText) return '';
  const [year, month] = String(monthText).split('-');
  const monthNumber = Number(month);
  if (!year || !Number.isInteger(monthNumber) || monthNumber < 1 || monthNumber > 12) {
    return String(monthText);
  }
  const date = new Date(Number(year), monthNumber - 1, 1);
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
};

export default function AUCPage() {
  // 状态管理
  const [currentMonth, setCurrentMonth] = useState('');
  const [monthOptions, setMonthOptions] = useState([]);
  const [overviewData, setOverviewData] = useState(null);
  const [trendsData, setTrendsData] = useState(null);
  const [tierDistribution, setTierDistribution] = useState([]);
  const [assetAllocation, setAssetAllocation] = useState([]);
  const [topClients, setTopClients] = useState([]);
  const [topClientsVisible, setTopClientsVisible] = useState(false);
  const [topClientsLoading, setTopClientsLoading] = useState(false);
  const [clientTypeFilter, setClientTypeFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [trendViewMode, setTrendViewMode] = useState('both'); // 'both', 'assets', 'inflow'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('analysis'); // 'analysis', 'distribution'
  const [allocationCurrency, setAllocationCurrency] = useState('all'); // 'all', 'USD', 'CNY', etc.
  const hasLoadedData = Boolean(
    overviewData ||
    trendsData ||
    tierDistribution.length ||
    assetAllocation.length
  );

  const monthSelectOptions = useMemo(() => (
    monthOptions.map((item) => ({
      value: item.month,
      label: item.label,
    }))
  ), [monthOptions]);

  const currentMonthLabel = useMemo(() => {
    const found = monthOptions.find((item) => item.month === currentMonth);
    return found?.label || formatMonthLabel(currentMonth);
  }, [monthOptions, currentMonth]);

  useEffect(() => {
    const fetchMonthOptions = async () => {
      try {
        const response = await aucAPI.getMonthOptions();
        const options = (response?.options || []).filter((item) => item.has_data);
        const selectedMonth = response?.selected_month || options[0]?.month || '';
        setMonthOptions(options);
        setCurrentMonth(selectedMonth);
      } catch (err) {
        console.error('Failed to load AUC month options:', err);
        const now = new Date();
        const fallbackMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        setMonthOptions([
          {
            month: fallbackMonth,
            label: formatMonthLabel(fallbackMonth),
          },
        ]);
        setCurrentMonth(fallbackMonth);
      }
    };

    fetchMonthOptions();
  }, []);

  // 获取所有数据
  useEffect(() => {
    const fetchData = async () => {
      if (!currentMonth) {
        return;
      }

      try {
        setLoading(true);
        setError(null);

        console.log('Starting to fetch AUC data...');

        // 并行调用所有 API
        const [overview, trends, tierDist, assetAlloc] = await Promise.all([
          aucAPI.getOverview({ month: currentMonth }),
          aucAPI.getTrends({ year: parseInt(currentMonth.split('-')[0]), limit_months: 12 }),
          aucAPI.getTierDistribution({ month: currentMonth }),
          aucAPI.getAssetAllocation({ month: currentMonth }),
        ]);

        const resolvedMonth = overview?.month || tierDist?.month || assetAlloc?.month;
        if (resolvedMonth && resolvedMonth !== currentMonth) {
          setCurrentMonth(resolvedMonth);
        }

        setOverviewData(overview);
        setTrendsData(trends);
        
        // 处理分级分布数据 - 从 tier-distribution API 获取
        if (tierDist && tierDist.data) {
          const distribution = tierDist.data;
          const tierDataRaw = [
            { tier: '< $10k (Mass)', clients: distribution['< $10k (Mass)'] || 0, color: '#E0E0E0' },
            { tier: '$10k - $100k (Core)', clients: distribution['$10k - $100k (Core)'] || 0, color: '#1A1A5A' },
            { tier: '$100k - $1M (Affluent)', clients: distribution['$100k - $1M (Affluent)'] || 0, color: '#FF8C00' },
            { tier: '> $1M (HNW)', clients: distribution['> $1M (HNW)'] || 0, color: '#1A1A1A' },
          ];
          
          // 计算总数和百分比
          const totalClients = tierDataRaw.reduce((sum, item) => sum + item.clients, 0);
          const tierData = tierDataRaw.map(item => ({
            ...item,
            percentage: totalClients > 0 ? (item.clients / totalClients) * 100 : 0
          }));
          
          setTierDistribution(tierData);
        } else {
          setTierDistribution([]);
        }

        // 处理资产配置数据
        if (assetAlloc && assetAlloc.data) {
          setAssetAllocation(assetAlloc.data);
        } else {
          setAssetAllocation([]);
        }
      } catch (err) {
        console.error('Failed to load AUC data:', err);
        setError(err.message || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [currentMonth]);

  // 获取Top客户数据
  const fetchTopClients = async (clientType = 'all') => {
    try {
      setTopClientsLoading(true);
      const response = await aucAPI.getTopClients({
        month: currentMonth,
        client_type: clientType,
        limit: 200
      });
      setTopClients(response.data || []);
    } catch (err) {
      console.error('Failed to load top clients:', err);
    } finally {
      setTopClientsLoading(false);
    }
  };

  // 显示Top客户模态框
  const showTopClientsModal = () => {
    setTopClientsVisible(true);
    setCurrentPage(1); // 重置到第一页
    fetchTopClients(clientTypeFilter);
  };

  // 隐藏Top客户模态框
  const hideTopClientsModal = () => {
    setTopClientsVisible(false);
  };

  // 客户类型筛选变化
  const handleClientTypeChange = (value) => {
    setClientTypeFilter(value);
    if (topClientsVisible) {
      fetchTopClients(value);
    }
  };

  // 构建 AUC 趋势图表配置
  const trendChartOption = useMemo(() => {
    if (!trendsData || !trendsData.months) {
      return {};
    }

    // 根据显示模式决定series配置
    let series = [];
    let legendData = [];
    let yAxis = [];

    if (trendViewMode === 'both' || trendViewMode === 'assets') {
      series.push({
        name: 'Total Assets',
        type: 'line',
        data: trendsData.total_assets || [],
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#E6B800' },  // 深黄色，比线条颜色#FFCC00更深
        lineStyle: { color: '#FFCC00', width: 3 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(255, 204, 0, 0.25)' },
              { offset: 1, color: 'rgba(255, 204, 0, 0)' },
            ],
          },
        },
      });
      legendData.push('Total Assets');
    }

    if (trendViewMode === 'both' || trendViewMode === 'inflow') {
      series.push({
        name: 'Net Inflow',
        type: 'line',
        data: trendsData.net_inflow || [],
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#F21627' },
        lineStyle: { color: '#CF1322', width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(207, 19, 34, 0.25)' },
              { offset: 1, color: 'rgba(207, 19, 34, 0)' },
            ],
          },
        },
        yAxisIndex: trendViewMode === 'both' ? 1 : 0,  // 单独显示时使用主Y轴
      });
      legendData.push('Net Inflow');
    }

    // 配置Y轴
    if (trendViewMode === 'both') {
      yAxis = [
        {
          type: 'value',
          axisLine: { show: false },
          splitLine: { lineStyle: { color: '#F0F0F0' } },
          axisLabel: { color: '#999', formatter: (v) => (v / 1000000).toFixed(0) + 'M' },
        },
        {
          type: 'value',
          axisLine: { show: false },
          splitLine: { show: false },
          axisLabel: { color: '#1890FF', formatter: (v) => (v / 1000000).toFixed(1) + 'M' },
        }
      ];
    } else {
      yAxis = [
        {
          type: 'value',
          axisLine: { show: false },
          splitLine: { lineStyle: { color: '#F0F0F0' } },
          axisLabel: { 
            color: '#999', 
            formatter: (v) => (v / 1000000).toFixed(trendViewMode === 'inflow' ? 1 : 0) + 'M' 
          },
        }
      ];
    }

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          let result = params[0].axisValue + '<br/>';
          params.forEach((p) => {
            const value = p.seriesName === 'Net Inflow' 
              ? (p.value / 1000000).toFixed(1) + 'M'
              : (p.value / 1000000).toFixed(0) + 'M';
            result += `${p.marker} ${p.seriesName}: $${value}<br/>`;
          });
          return result;
        },
      },
      legend: {
        top: 10,
        right: 20,
        data: legendData,
        textStyle: { fontSize: 12 },
      },
      grid: { left: 60, right: 20, top: 50, bottom: 30 },
      xAxis: {
        type: 'category',
        data: trendsData.months,
        axisLine: { lineStyle: { color: '#E8E8E8' } },
        axisLabel: { color: '#999' },
      },
      yAxis,
      series,
    };
  }, [trendsData, trendViewMode]);

  const allocationDisplayData = useMemo(() => {
    if (!assetAllocation?.length) return [];

    if (allocationCurrency !== 'all') {
      return assetAllocation.filter(item => item.currency === allocationCurrency);
    }

    const amountByCategory = new Map();
    assetAllocation.forEach((item) => {
      const category = item.name;
      const amount = Number(item.amount || 0);
      amountByCategory.set(category, (amountByCategory.get(category) || 0) + amount);
    });

    const totalAmount = Array.from(amountByCategory.values()).reduce((sum, amount) => sum + amount, 0);
    return Array.from(amountByCategory.entries()).map(([name, amount]) => ({
      name,
      amount,
      percentage: totalAmount > 0 ? Number(((amount / totalAmount) * 100).toFixed(2)) : 0,
      currency: 'all',
    }));
  }, [assetAllocation, allocationCurrency]);

  const allocationChartData = useMemo(() => (
    allocationDisplayData.map((item, index) => ({
      ...item,
      color: ALLOCATION_CHART_COLORS[index % ALLOCATION_CHART_COLORS.length],
    }))
  ), [allocationDisplayData]);

  // 构建资产配置饼表配置
  const buildAllocationOption = useMemo(() => {
    const pieData = allocationChartData.map((item) => ({
      value: Number(item.amount || 0),
      name: item.name,
      itemStyle: { color: item.color },
    }));

    return {
      tooltip: {
        trigger: 'item',
        formatter: (params) => `${params.name}: ${Number(params.percent || 0).toFixed(1)}%`,
      },
      legend: { show: false },
      series: [{
        type: 'pie',
        radius: ['50%', '75%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{d}%',
          fontSize: 11,
        },
        data: pieData,
      }],
      graphic: [{
        type: 'text',
        left: 'center',
        top: 'center',
        style: {
          text: `Total\n${allocationChartData.length ? '100%' : '0%'}`,
          textAlign: 'center',
          fontSize: 14,
          fontWeight: 600,
          fill: '#333',
        },
      }],
    };
  }, [allocationChartData]);

  // 如果有错误，显示错误信息
  if (error) {
    return (
      <div className="auc-page">
        <PageHeader
          title="资产托管 (AUC) 深度分析看板"
          breadcrumb={['综合分析', '资产托管 (AUC)']}
        />
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Text type="danger">加载数据失败: {error}</Text>
        </div>
      </div>
    );
  }

  // 如果数据还在加载，显示骨架屏
  if (loading && !hasLoadedData) {
    return (
      <div className="auc-page">
        <PageHeader
          title="资产托管 (AUC) 深度分析看板"
          breadcrumb={['综合分析', '资产托管 (AUC)']}
        />
        <Row gutter={16} wrap={false} style={{ marginBottom: 24 }}>
          {[...Array(4)].map((_, i) => (
            <Col key={i} span={6}>
              <Card bodyStyle={{ padding: '20px' }}>
                <Skeleton active />
              </Card>
            </Col>
          ))}
        </Row>
        <Row gutter={16} wrap={false} style={{ marginBottom: 24 }}>
          <Col span={16}>
            <Card title="资产规模趋势 (12个月)" bodyStyle={{ padding: '12px 16px' }}>
              <Skeleton.Image style={{ width: '100%', height: 300 }} />
            </Card>
          </Col>
          <Col span={8}>
            <Card title="资产等级分布" bodyStyle={{ padding: '16px 20px' }}>
              <Skeleton active />
            </Card>
          </Col>
        </Row>
      </div>
    );
  }

  // 构建 StatCard 的数据
  const formatDetailedNumber = (value, decimals = 2) => Number(value || 0).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  const formatCompactCurrency = (value) => {
    const amount = Number(value || 0);
    if (!Number.isFinite(amount)) return '$0';
    const absAmount = Math.abs(amount);

    if (absAmount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
    if (absAmount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
    if (absAmount >= 1_000) return `$${(amount / 1_000).toFixed(1)}k`;
    return `$${amount.toFixed(2)}`;
  };

  const statCardData = [
    {
      title: '总资产规模',
      value: overviewData?.total_auc?.formatted || '$0M',
      fullValue: `$${formatDetailedNumber(overviewData?.total_auc?.value, 2)}`,
      toggleValue: true,
      change: overviewData?.total_auc?.yoy_change || 0,
      icon: <BankOutlined />,
      iconBg: '#FFF3B0',
      iconColor: '#E6B800',
    },
    {
      title: '平均账户资产',
      value: formatCompactCurrency(overviewData?.avg_account?.value),
      fullValue: `$${formatDetailedNumber(overviewData?.avg_account?.value, 2)}`,
      toggleValue: true,
      changeLabel: `Health: ${overviewData?.avg_account?.health || 'Fair'}`,
      icon: <UserOutlined />,
      iconBg: '#E8F5E9',
      iconColor: '#52C41A',
    },
    {
      title: '资产留存率',
      value: overviewData?.retention_rate?.formatted || '0%',
      fullValue: `${formatDetailedNumber(overviewData?.retention_rate?.value, 2)}%`,
      toggleValue: true,
      change: overviewData?.retention_rate?.change || 0,
      icon: <SafetyOutlined />,
      iconBg: '#E3F2FD',
      iconColor: '#1890FF',
    },
    {
      title: '本月净流入',
      value: overviewData?.net_inflow?.formatted || '$0M',
      fullValue: `$${formatDetailedNumber(overviewData?.net_inflow?.value, 2)}`,
      toggleValue: true,
      change: overviewData?.net_inflow?.change_pct || 0,
      icon: <ArrowUpOutlined />,
      iconBg: '#FFF3E0',
      iconColor: '#FF8C00',
    },
  ];

  return (
    <div className="auc-page">
      <PageHeader
        title="资产托管 (AUC) 深度分析看板"
        breadcrumb={['综合分析', '资产托管 (AUC)']}
        extra={
          <Space>
            <Select
              value={currentMonth}
              onChange={setCurrentMonth}
              size="small"
              style={{ width: 120 }}
              options={monthSelectOptions}
            />
          </Space>
        }
      />

      <Tabs className="auc-tabs" activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane tab="AUC 分析" key="analysis">
          {/* Stat Cards */}
          <Row gutter={16} wrap={false} style={{ marginBottom: 24 }}>
            {statCardData.map((item, idx) => (
              <Col key={idx} span={6}>
                <StatCard {...item} />
              </Col>
            ))}
          </Row>

          {/* AUC Trend + Tier Distribution */}
          <Row gutter={16} wrap={false} style={{ marginBottom: 24 }}>
            <Col span={16}>
              <Card 
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>资产规模趋势 (12个月)</span>
                    <Space size="small">
                      <Button 
                        size="small" 
                        type={trendViewMode === 'both' ? 'primary' : 'default'}
                        onClick={() => setTrendViewMode('both')}
                      >
                        全部显示
                      </Button>
                      <Button 
                        size="small" 
                        type={trendViewMode === 'assets' ? 'primary' : 'default'}
                        onClick={() => setTrendViewMode('assets')}
                      >
                        仅资产
                      </Button>
                      <Button 
                        size="small" 
                        type={trendViewMode === 'inflow' ? 'primary' : 'default'}
                        onClick={() => setTrendViewMode('inflow')}
                      >
                        仅流入
                      </Button>
                    </Space>
                  </div>
                }
                className="chart-card" 
                bodyStyle={{ padding: '12px 16px' }}
              >
                <ReactECharts 
                  key={trendViewMode} 
                  option={trendChartOption} 
                  style={{ height: 300 }} 
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card title="资产等级分布" className="chart-card" bodyStyle={{ padding: '16px 20px' }}>
                <div className="tier-list">
                  {tierDistribution.map((item) => (
                    <div key={item.tier} className="tier-item">
                      <div className="tier-info">
                        <Text style={{ fontSize: 13 }}>{item.tier}</Text>
                        <Text strong>{item.clients.toLocaleString()} clients ({item.percentage.toFixed(1)}%)</Text>
                      </div>
                      <div className="tier-bar-bg">
                        <div
                          className="tier-bar"
                          style={{
                            width: `${item.percentage}%`,
                            backgroundColor: item.color,
                            height: '12px',
                            transition: 'width 0.8s ease-in-out',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <a 
                  className="view-all-link" 
                  style={{ color: '#FF8C00', marginTop: 16, display: 'block', cursor: 'pointer' }}
                  onClick={showTopClientsModal}
                >
                  查看客户列表 →
                </a>
              </Card>
            </Col>
          </Row>
        </Tabs.TabPane>

        <Tabs.TabPane tab="AUC 分布分析" key="distribution">
          {/* Asset Allocation */}
          <Row gutter={16} wrap={false}>
            <Col span={12}>
              <Card title="资产构成 (Asset Allocation)" className="chart-card" bodyStyle={{ padding: '12px' }}>
                <ReactECharts option={buildAllocationOption} style={{ height: 280 }} />
              </Card>
            </Col>
            <Col span={12}>
              <Card className="chart-card" bodyStyle={{ padding: '16px 20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 15 }}>资产配置详情</Text>
                  <Select
                    value={allocationCurrency}
                    onChange={setAllocationCurrency}
                    style={{ width: 100 }}
                    size="small"
                  >
                    <Select.Option value="all">全部币种</Select.Option>
                    <Select.Option value="USD">USD</Select.Option>
                    <Select.Option value="CNY">CNY</Select.Option>
                    <Select.Option value="EUR">EUR</Select.Option>
                    <Select.Option value="NZD">NZD</Select.Option>
                    <Select.Option value="HKD">HKD</Select.Option>
                    <Select.Option value="AUD">AUD</Select.Option>
                  </Select>
                </div>
                <div style={{ marginTop: 16 }}>
                  {allocationChartData.map((item) => (
                    <div key={`${item.currency}-${item.name}`} className="allocation-detail-item">
                      <div className="allocation-detail-label">
                        <span className="allocation-detail-dot" style={{ background: item.color }} />
                        <Text>{item.name}</Text>
                      </div>
                      <Text strong>{item.percentage}%</Text>
                    </div>
                  ))}
                </div>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  Base currency normalized to USD equivalent
                </Text>
              </Card>
            </Col>
          </Row>
        </Tabs.TabPane>
      </Tabs>

      {/* Top Clients Modal */}
      <Modal
        title={`Top 客户排行 - ${currentMonthLabel}`}
        open={topClientsVisible}
        onCancel={hideTopClientsModal}
        width={1000}
        footer={null}
      >
        <Space style={{ marginBottom: 16 }}>
          <Text>客户类型筛选:</Text>
          <Select
            value={clientTypeFilter}
            onChange={handleClientTypeChange}
            style={{ width: 120 }}
            options={[
              { value: 'all', label: '全部' },
              { value: 'HNW', label: 'HNW' },
              { value: 'S-Class', label: 'S-Class' },
              { value: 'Frequent Trader', label: 'Frequent Trader' },
              { value: 'New', label: 'New' },
            ]}
          />
        </Space>

        <Table
          dataSource={topClients}
          loading={topClientsLoading}
          rowKey="uid"
          pagination={{
            current: currentPage,
            pageSize: 10,
            showSizeChanger: false,
            showQuickJumper: true,
            showTotal: (total, range) => `共 ${total} 条记录，显示 ${range[0]}-${range[1]} 条`,
            onChange: (page) => setCurrentPage(page)
          }}
          columns={[
            {
              title: '排名',
              render: (_, __, index) => {
                return (currentPage - 1) * 10 + index + 1;
              },
              width: 80,
            },
            {
              title: '客户UID',
              dataIndex: 'uid',
              width: 100,
            },
            {
              title: '姓名',
              dataIndex: 'name',
              width: 120,
            },
            {
              title: '客户类型',
              dataIndex: 'client_type',
              width: 120,
              render: (type) => (
                <Tag color={
                  type === 'HNW' ? 'gold' :
                  type === 'S-Class' ? 'blue' :
                  type === 'Frequent Trader' ? 'green' : 'default'
                }>
                  {type}
                </Tag>
              ),
            },
            {
              title: '净资产',
              dataIndex: 'net_assets',
              render: (value) => `$${value?.toLocaleString() || 0}`,
              sorter: (a, b) => (a.net_assets || 0) - (b.net_assets || 0),
              defaultSortOrder: 'descend',
            },
            {
              title: '月交易次数',
              dataIndex: 'monthly_trade_count',
              width: 120,
            },
            {
              title: '标签',
              dataIndex: 'tags',
              render: (tags) => (
                <>
                  {tags?.map(tag => (
                    <Tag key={tag} size="small">{tag}</Tag>
                  ))}
                </>
              ),
            },
          ]}
        />
      </Modal>
    </div>
  );
}
