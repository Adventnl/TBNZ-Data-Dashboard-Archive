import { Row, Col, Card, Table, Select, Input, Button, Typography, Avatar, Space, Badge, Tabs, Alert } from 'antd';
import {
  UserAddOutlined,
  UserDeleteOutlined,
  RocketOutlined,
  SearchOutlined,
  CaretUpOutlined,
  CaretDownOutlined,
} from '@ant-design/icons';
import { useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../../components';
import { rankingsAPI, tradingAPI } from '../../services/api';
import './RankingsPage.css';

const { Text, Title } = Typography;

function MovementCard({ title, count, countColor, items }) {
  const [expanded, setExpanded] = useState(true);
  const accentColor = title === 'Dropped Out' ? '#FF4D4F' : title === 'New Entry' ? '#52C41A' : '#FF8C00';

  return (
    <div className="movement-section">
      <button
        type="button"
        className="movement-header movement-toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded((prev) => !prev)}
      >
        <div className="movement-header-main">
          <span className="movement-dot" style={{ background: accentColor }} />
          <Text strong>{title}</Text>
          <Badge count={count} style={{ backgroundColor: countColor || '#52C41A' }} />
        </div>
        <div className="movement-header-action">
          <Text type="secondary" style={{ fontSize: 12 }}>{expanded ? '收起' : '展开'}</Text>
          {expanded ? <CaretUpOutlined style={{ color: '#8C8C8C' }} /> : <CaretDownOutlined style={{ color: '#8C8C8C' }} />}
        </div>
      </button>
      {expanded && (
        <div className="movement-list">
          {items.length === 0 ? (
            <Text type="secondary" style={{ fontSize: 12 }}>暂无数据</Text>
          ) : (
            items.map((item, idx) => (
              <div key={`${item.uid}-${idx}`} className="movement-item">
                <Avatar size={32} style={{ background: title === 'Dropped Out' ? '#FFF2F0' : '#F6FFED', color: title === 'Dropped Out' ? '#FF4D4F' : '#52C41A', fontWeight: 600, fontSize: 14 }}>
                  {(item.name || item.uid || '?').charAt(0)}
                </Avatar>
                <div className="movement-item-info">
                  <Text strong style={{ fontSize: 13 }}>{item.name || item.uid}</Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>UID: {item.uid}</Text>
                </div>
                <div className="movement-item-rank">
                  <Text strong style={{ color: title === 'Dropped Out' ? '#FF4D4F' : '#52C41A' }}>
                    No. {item.rank}
                  </Text>
                  <Text className="movement-item-from-rank" type="secondary" style={{ fontSize: 11 }}>from No. {item.from}</Text>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function RankingsPage() {
  const [month, setMonth] = useState('');
  const [movementTopN, setMovementTopN] = useState(200);
  const [availableMonths, setAvailableMonths] = useState([]);
  const [availableClientTypes, setAvailableClientTypes] = useState([]);
  const [availableNationalities, setAvailableNationalities] = useState([]);
  const [activeTab, setActiveTab] = useState('leaderboard');
  const [nationalityFilter, setNationalityFilter] = useState('all');
  const [contributors, setContributors] = useState([]);
  const [contributorsLoading, setContributorsLoading] = useState(false);
  const [overview, setOverview] = useState({
    changed_count: 0,
    new_entry_count: 0,
    dropped_out_count: 0,
    big_jump_count: 0,
  });
  const [movements, setMovements] = useState({
    new_entries: [],
    dropped_out: [],
    big_jumps: [],
  });
  const [tableRows, setTableRows] = useState([]);
  const [showFilteredRank, setShowFilteredRank] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [clientTypeFilter, setClientTypeFilter] = useState('all');
  const [tablePagination, setTablePagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [tableSort, setTableSort] = useState({ field: 'rank', order: 'ascend' });
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [movementsLoading, setMovementsLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadOverviewAndMovements = async (selectedMonth, selectedNationality, selectedTopN) => {
    setOverviewLoading(true);
    setMovementsLoading(true);
    setError(null);
    try {
      const [overviewRes, movementsRes] = await Promise.all([
        rankingsAPI.getOverview({
          month: selectedMonth || undefined,
          dimension: 'trading',
          nationality: selectedNationality !== 'all' ? selectedNationality : undefined,
          top_n: selectedTopN,
        }),
        rankingsAPI.getMovements({
          month: selectedMonth || undefined,
          dimension: 'trading',
          nationality: selectedNationality !== 'all' ? selectedNationality : undefined,
          top_n: selectedTopN,
          limit: 6,
        }),
      ]);

      setOverview(overviewRes.summary || {
        changed_count: 0,
        new_entry_count: 0,
        dropped_out_count: 0,
        big_jump_count: 0,
      });
      setMovements({
        new_entries: movementsRes.new_entries || [],
        dropped_out: movementsRes.dropped_out || [],
        big_jumps: movementsRes.big_jumps || [],
      });

      const months = overviewRes.available_months || [];
      if (months.length > 0) {
        setAvailableMonths(months);
      }
      setAvailableNationalities(overviewRes.nationality_options || []);
      if (overviewRes.month && overviewRes.month !== month) {
        setMonth(overviewRes.month);
      }
      if (overviewRes.top_n && overviewRes.top_n !== movementTopN) {
        setMovementTopN(overviewRes.top_n);
      }
    } catch (err) {
      setError(err.message || '加载排名概览失败');
    } finally {
      setOverviewLoading(false);
      setMovementsLoading(false);
    }
  };

  const loadTable = async () => {
    setTableLoading(true);
    setError(null);
    try {
      const params = {
        month: month || undefined,
        top_n: movementTopN,
        page: tablePagination.current,
        page_size: tablePagination.pageSize,
        sort_by: tableSort.field,
        sort_order: tableSort.order,
        keyword: searchKeyword || undefined,
        client_type: clientTypeFilter,
        nationality: nationalityFilter !== 'all' ? nationalityFilter : undefined,
      };
      const response = await rankingsAPI.getTop500Trading(params);

      setTableRows(response.items || []);
      setShowFilteredRank(Boolean(response.has_active_filters));
      setAvailableClientTypes(response.client_type_options || []);
      setAvailableNationalities(response.nationality_options || []);
      setTablePagination((prev) => ({
        ...prev,
        current: response.page || prev.current,
        pageSize: response.page_size || prev.pageSize,
        total: response.total || 0,
      }));
      if ((response.available_months || []).length > 0) {
        setAvailableMonths(response.available_months);
      }
      if (response.month && response.month !== month) {
        setMonth(response.month);
      }
    } catch (err) {
      setError(err.message || `加载Top ${movementTopN}数据失败`);
    } finally {
      setTableLoading(false);
    }
  };

  const loadContributors = async () => {
    setContributorsLoading(true);
    setError(null);
    try {
      const response = await tradingAPI.getTopContributors({
        page: tablePagination.current,
        page_size: tablePagination.pageSize,
        sort_by: tableSort.field,
        order: tableSort.order === 'descend' ? 'desc' : 'asc',
      });
      setContributors(response.items || []);
      setTablePagination((prev) => ({
        ...prev,
        current: response.page || prev.current,
        pageSize: response.page_size || prev.pageSize,
        total: response.total || 0,
      }));
    } catch (err) {
      setError(err.message || '加载核心贡献用户失败');
    } finally {
      setContributorsLoading(false);
    }
  };

  useEffect(() => {
    loadOverviewAndMovements(month, nationalityFilter, movementTopN);
  }, [month, nationalityFilter, movementTopN]);

  useEffect(() => {
    if (activeTab !== 'leaderboard') {
      return;
    }
    loadTable();
  }, [activeTab, month, movementTopN, tablePagination.current, tablePagination.pageSize, tableSort.field, tableSort.order, searchKeyword, clientTypeFilter, nationalityFilter]);

  useEffect(() => {
    if (activeTab !== 'contributors') {
      return;
    }
    loadContributors();
  }, [activeTab, tablePagination.current, tablePagination.pageSize, tableSort.field, tableSort.order]);

  const formatMonthLabel = (monthText) => {
    if (!monthText) return '';
    const [year, mon] = String(monthText).split('-');
    const monthNumber = Number(mon);
    if (!year || !Number.isInteger(monthNumber) || monthNumber < 1 || monthNumber > 12) {
      return String(monthText);
    }
    return new Date(Number(year), monthNumber - 1, 1)
      .toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  const monthOptions = useMemo(
    () => availableMonths.map((item) => ({ value: item, label: formatMonthLabel(item) })),
    [availableMonths],
  );

  const movementTopNOptions = useMemo(
    () => [100, 200, 300, 500].map((value) => ({ value, label: `Top ${value}` })),
    [],
  );

  const clientTypeOptions = useMemo(() => {
    return [
      { value: 'all', label: '全部客户类型' },
      ...availableClientTypes.map((value) => ({ value, label: value })),
    ];
  }, [availableClientTypes]);

  const nationalityOptions = useMemo(() => {
    return [
      { value: 'all', label: '全部国籍' },
      ...availableNationalities.map((value) => ({ value, label: value })),
    ];
  }, [availableNationalities]);

  const top500Columns = useMemo(() => {
    const overallRankColumn = {
      title: showFilteredRank ? '大排名' : '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 72,
      align: 'center',
      sorter: true,
      render: (rank) => (
        <span className={`rank-number ${rank <= 3 ? `top-${rank}` : ''}`}>
          {rank}
        </span>
      ),
    };

    const detailColumns = [
      {
        title: 'UID',
        dataIndex: 'uid',
        key: 'uid',
        width: 126,
        render: (_, record) => (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Avatar size={26} style={{ background: '#F0F0F0', color: '#666', fontWeight: 600, fontSize: 12 }}>
              {(record.name || record.uid || '?').charAt(0)}
            </Avatar>
            <div style={{ lineHeight: 1.2 }}>
              <Text strong style={{ fontSize: 12 }}>{record.uid}</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 10 }}>{record.name || '-'}</Text>
            </div>
          </div>
        ),
      },
      {
        title: '邀请码/渠道',
        dataIndex: 'channel_source',
        key: 'channel_source',
        width: 116,
        ellipsis: true,
      },
      {
        title: '国籍',
        dataIndex: 'nationality',
        key: 'nationality',
        width: 84,
        sorter: true,
        render: (value) => value || '-',
      },
      {
        title: '客户类型',
        dataIndex: 'client_type',
        key: 'client_type',
        width: 108,
        ellipsis: true,
      },
      {
        title: '排名变动',
        dataIndex: 'rank_change',
        key: 'rank_change',
        width: 98,
        sorter: true,
        render: (change) => {
          if (change === 0) return <span style={{ color: '#999' }}>— 无变化</span>;
          if (change > 0) {
            return (
              <span style={{ color: '#52C41A' }}>
                <CaretUpOutlined /> +{change}
              </span>
            );
          }
          return (
            <span style={{ color: '#FF4D4F' }}>
              <CaretDownOutlined /> {Math.abs(change)}
            </span>
          );
        },
      },
      {
        title: '交易量',
        dataIndex: 'trading_volume',
        key: 'trading_volume',
        width: 98,
        sorter: true,
        render: (value) => Number(value || 0).toLocaleString(),
      },
    ];

    if (!showFilteredRank) {
      return [overallRankColumn, ...detailColumns];
    }

    const filteredRankColumn = {
      title: '当前排名',
      dataIndex: 'filtered_rank',
      key: 'filtered_rank',
      width: 106,
      align: 'center',
      sorter: true,
      render: (rank) => (
        <span className={`rank-number ${rank <= 3 ? `top-${rank}` : ''}`}>
          {rank}
        </span>
      ),
    };

    return [filteredRankColumn, overallRankColumn, ...detailColumns];
  }, [showFilteredRank]);

  const contributorColumns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 70,
      align: 'center',
      sorter: true,
      render: (rank) => <span className={`rank-number ${rank <= 3 ? `top-${rank}` : ''}`}>{rank}</span>,
    },
    {
      title: '市场',
      dataIndex: 'market',
      key: 'market',
      width: 90,
      sorter: true,
    },
    {
      title: '国籍',
      dataIndex: 'nationality',
      key: 'nationality',
      width: 84,
      sorter: true,
      render: (value) => value || '-',
    },
    {
      title: '客户 UID',
      dataIndex: 'uid',
      key: 'uid',
      width: 120,
      render: (_, record) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Avatar size={26} style={{ background: '#F0F0F0', color: '#666', fontWeight: 600, fontSize: 12 }}>
            {(record.name || record.uid || '?').charAt(0)}
          </Avatar>
          <div style={{ lineHeight: 1.2 }}>
            <Text strong style={{ fontSize: 12 }}>{record.uid}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 10 }}>{record.name || '-'}</Text>
          </div>
        </div>
      ),
    },
    {
      title: '交易量',
      dataIndex: 'volume',
      key: 'volume',
      width: 120,
      sorter: true,
      render: (value) => Number(value || 0).toLocaleString(),
    },
    {
      title: '占比 (%)',
      dataIndex: 'contribution_pct',
      key: 'contribution_pct',
      width: 100,
      sorter: true,
      render: (value) => `${Number(value || 0).toFixed(2)}%`,
    },
    {
      title: '环比变动 (%)',
      dataIndex: 'change_pct',
      key: 'change_pct',
      width: 120,
      sorter: true,
      render: (value) => (
        <span style={{ color: Number(value || 0) >= 0 ? '#52C41A' : '#FF4D4F' }}>
          {Number(value || 0) >= 0 ? '+' : ''}{Number(value || 0).toFixed(2)}%
        </span>
      ),
    },
  ];

  const handleTableChange = (pagination, _, sorter) => {
    setTablePagination((prev) => ({
      ...prev,
      current: pagination.current,
      pageSize: pagination.pageSize,
    }));
    if (sorter?.field) {
      setTableSort({ field: sorter.field, order: sorter.order || 'ascend' });
    }
  };

  return (
    <div className="rankings-page">
      <PageHeader
        title="客户排名变化"
        breadcrumb={['综合分析', '客户排名变化']}
        extra={
          <Space>
            <Select
              value={movementTopN}
              size="small"
              style={{ width: 120 }}
              options={movementTopNOptions}
              onChange={(value) => {
                setMovementTopN(value);
                setTablePagination((prev) => ({ ...prev, current: 1 }));
              }}
              placeholder="选择范围"
            />
            <Select
              value={month}
              size="small"
              style={{ width: 140 }}
              options={monthOptions}
              onChange={(value) => {
                setMonth(value);
                setTablePagination((prev) => ({ ...prev, current: 1 }));
              }}
              placeholder="选择月份"
            />
          </Space>
        }
      />

      {error && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="加载失败"
          description={error}
        />
      )}

      {/* Summary Cards */}
      <Row gutter={16} wrap={false} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card className="summary-card" bodyStyle={{ padding: '20px 24px' }} loading={overviewLoading}>
            <div className="summary-card-inner">
              <div>
                <Text type="secondary">{`本月变动数量 (Top ${movementTopN})`}</Text>
                <Title level={2} style={{ margin: '4px 0 0' }}>
                  {overview.changed_count}<span className="summary-unit">位客户</span>
                </Title>
              </div>
              <div className="summary-icon" style={{ background: '#FFF7E6' }}>
                <RocketOutlined style={{ fontSize: 24, color: '#FA8C16' }} />
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="summary-card" bodyStyle={{ padding: '20px 24px' }} loading={overviewLoading}>
            <div className="summary-card-inner">
              <div>
                <Text type="secondary">{`New Entry (Top ${movementTopN})`}</Text>
                <Title level={2} style={{ margin: '4px 0 0' }}>
                  {overview.new_entry_count}<span className="summary-unit">位客户</span>
                </Title>
              </div>
              <div className="summary-icon" style={{ background: '#E8F5E9' }}>
                <UserAddOutlined style={{ fontSize: 24, color: '#52C41A' }} />
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="summary-card" bodyStyle={{ padding: '20px 24px' }} loading={overviewLoading}>
            <div className="summary-card-inner">
              <div>
                <Text type="secondary">{`Dropped Out (Top ${movementTopN})`}</Text>
                <Title level={2} style={{ margin: '4px 0 0', color: '#FF4D4F' }}>
                  {overview.dropped_out_count}<span className="summary-unit">位客户</span>
                </Title>
              </div>
              <div className="summary-icon" style={{ background: '#FFF2F0' }}>
                <UserDeleteOutlined style={{ fontSize: 24, color: '#FF4D4F' }} />
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="summary-card" bodyStyle={{ padding: '20px 24px' }} loading={overviewLoading}>
            <div className="summary-card-inner">
              <div>
                <Text type="secondary">{`排名大幅提升 (&gt;20名, Top ${movementTopN})`}</Text>
                <Title level={2} style={{ margin: '4px 0 0' }}>
                  {overview.big_jump_count}<span className="summary-unit">位客户</span>
                </Title>
              </div>
              <div className="summary-icon" style={{ background: '#FFF3E0' }}>
                <RocketOutlined style={{ fontSize: 24, color: '#FF8C00' }} />
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Movement Cards + Leaderboard */}
      <Row gutter={16} wrap={false}>
        <Col span={5}>
          <Card className="movement-card" bodyStyle={{ padding: 0 }} loading={movementsLoading}>
            <MovementCard
              title="New Entry"
              count={overview.new_entry_count}
              countColor="#52C41A"
              items={movements.new_entries}
            />
            <MovementCard
              title="Dropped Out"
              count={overview.dropped_out_count}
              countColor="#FF4D4F"
              items={movements.dropped_out}
            />
            <MovementCard
              title="排名大幅提升"
              count={overview.big_jump_count}
              countColor="#FF8C00"
              items={movements.big_jumps}
            />
          </Card>
        </Col>
        <Col span={19}>
          <Card
            className="top200-card"
            bodyStyle={{ padding: 0 }}
          >
            <div className="top200-header">
              <Text strong className="top200-title" style={{ fontSize: 16 }}>
                {activeTab === 'leaderboard' ? `📊 Top ${movementTopN} 排行榜` : '📈 核心贡献用户排名'}
              </Text>
              <div className="top200-controls">
                <div className="top200-controls-row">
                  <Tabs
                    className="top200-dimension-tabs"
                    activeKey={activeTab}
                    onChange={(value) => {
                      setActiveTab(value);
                      setTablePagination((prev) => ({ ...prev, current: 1 }));
                      setTableSort({ field: 'rank', order: 'ascend' });
                    }}
                    items={[
                      { key: 'leaderboard', label: `Top ${movementTopN} 排行榜` },
                      { key: 'contributors', label: '核心贡献用户排名' },
                    ]}
                  />
                  {activeTab === 'leaderboard' && (
                    <>
                      <Select
                        value={nationalityFilter}
                        allowClear
                        size="small"
                        style={{ width: 140 }}
                        options={nationalityOptions}
                        placeholder="全部国籍"
                        onChange={(value) => {
                          setNationalityFilter(value || 'all');
                          setTablePagination((prev) => ({ ...prev, current: 1 }));
                        }}
                      />
                      <Select
                        value={clientTypeFilter}
                        size="small"
                        style={{ width: 152 }}
                        options={clientTypeOptions}
                        onChange={(value) => {
                          setClientTypeFilter(value);
                          setTablePagination((prev) => ({ ...prev, current: 1 }));
                        }}
                      />
                      <Input
                        size="small"
                        placeholder="搜索客户姓名或UID..."
                        prefix={<SearchOutlined />}
                        style={{ width: 188 }}
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                        onPressEnter={() => {
                          setSearchKeyword(searchInput.trim());
                          setTablePagination((prev) => ({ ...prev, current: 1 }));
                        }}
                      />
                      <Button
                        size="small"
                        onClick={() => {
                          setSearchKeyword(searchInput.trim());
                          setTablePagination((prev) => ({ ...prev, current: 1 }));
                        }}
                      >
                        搜索
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>
            <Table
              dataSource={activeTab === 'contributors' ? contributors : tableRows}
              columns={activeTab === 'contributors' ? contributorColumns : top500Columns}
              rowKey={(row) => `${row.uid}-${row.rank}`}
              size="small"
              loading={activeTab === 'contributors' ? contributorsLoading : tableLoading}
              onChange={handleTableChange}
              tableLayout="fixed"
              pagination={activeTab !== 'contributors' ? {
                size: 'small',
                current: tablePagination.current,
                total: tablePagination.total,
                pageSize: tablePagination.pageSize,
                showSizeChanger: true,
                showTotal: (total, range) => `Showing ${range[0]} to ${range[1]} of ${total} entries`,
              } : {
                size: 'small',
                current: tablePagination.current,
                total: tablePagination.total,
                pageSize: tablePagination.pageSize,
                showSizeChanger: true,
                showTotal: (total, range) => `Showing ${range[0]} to ${range[1]} of ${total} entries`,
              }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
