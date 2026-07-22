import { Card, Select, Input, Button, Spin, message } from 'antd';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import L from 'leaflet';
import './MapPage.css';
import { useEffect, useMemo, useState } from 'react';

const maleIcon = L.icon({
  iconUrl: '/laohu-logo.png',
  iconSize: [20, 20],
  iconAnchor: [10, 20],
  popupAnchor: [0, -20],
});

const femaleIcon = L.icon({
  iconUrl: '/laohu-logo-female.png',
  iconSize: [20, 20],
  iconAnchor: [10, 20],
  popupAnchor: [0, -20],
});

function ResetViewControl({ center, zoom }) {
  const map = useMap();

  return (
    <div className="leaflet-top leaflet-left custom-reset-control">
      <div className="leaflet-control leaflet-bar">
        <button
          type="button"
          className="reset-view-btn"
          onClick={() => map.setView(center, zoom)}
          title="回到初始位置"
        >
          ⌂
        </button>
      </div>
    </div>
  );
}

function MarkerClusterLayer({ points }) {
  const map = useMap();

  useEffect(() => {
    const clusterGroup = L.markerClusterGroup({
      chunkedLoading: true,
      showCoverageOnHover: false,
      spiderfyOnMaxZoom: true,
    });

    points.forEach((item, index) => {
      const marker = L.marker(
        [Number(item.latitude), Number(item.longitude)],
        {
          icon: item.gender === 'female' ? femaleIcon : maleIcon,
        }
      );

      const popupHtml = `
        <div style="min-width:220px;line-height:1.5;">
          <div><b>${item.name || 'Unknown'}</b></div>
          <div>UID: ${item.uid || '-'}</div>
          <div>用户类型: ${item.user_type || '-'}</div>
          <div>城市: ${item.city || '-'}</div>
          <div>地区: ${item.region || '-'}</div>
          <div>地址: ${item.address || '-'}</div>
          <div>性别: ${item.gender || '-'}</div>
          <div>年龄: ${item.age ?? '-'}</div>
          <div>年龄段: ${item.age_range || '-'}</div>
          <div>日期: ${item.activity_date || '-'}</div>
          <div>登录次数: ${item.login_count ?? 0}</div>
          <div>会话次数: ${item.session_count ?? 0}</div>
        </div>
      `;

      marker.bindPopup(popupHtml);
      marker.options.title = item.uid || item.user_id || String(index);
      clusterGroup.addLayer(marker);
    });

    map.addLayer(clusterGroup);

    return () => {
      map.removeLayer(clusterGroup);
      clusterGroup.clearLayers();
    };
  }, [map, points]);

  return null;
}

const userTypes = [
  { value: 'all', label: '全部' },
  { value: '注册用户', label: '注册用户' },
  { value: '已成功入金用户', label: '已成功入金用户' },
  { value: '完成第一笔交易用户', label: '完成第一笔交易用户' },
  { value: '高净值用户', label: '高净值用户' },
];

const months = [
  { value: 'all', label: '全部' },
  { value: 'Jan', label: '1月' },
  { value: 'Feb', label: '2月' },
  { value: 'Mar', label: '3月' },
  { value: 'Apr', label: '4月' },
  { value: 'May', label: '5月' },
  { value: 'Jun', label: '6月' },
  { value: 'Jul', label: '7月' },
  { value: 'Aug', label: '8月' },
  { value: 'Sep', label: '9月' },
  { value: 'Oct', label: '10月' },
  { value: 'Nov', label: '11月' },
  { value: 'Dec', label: '12月' },
];

const genderOptions = [
  { value: 'all', label: '全部' },
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
];

const ageRangeOptions = [
  { value: 'all', label: '全部' },
  { value: '18-30', label: '18 - 30' },
  { value: '30-45', label: '30 - 45' },
  { value: '45+', label: '45+' },
];

export default function MapPage() {
  const [mapUsers, setMapUsers] = useState([]);
  const [loading, setLoading] = useState(false);

  const [selectedUserType, setSelectedUserType] = useState('all');
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedRegion, setSelectedRegion] = useState('all');
  const [selectedGender, setSelectedGender] = useState('all');
  const [selectedAgeRange, setSelectedAgeRange] = useState('all');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [showInfoPanel, setShowInfoPanel] = useState(false);

  const initialCenter = [-41.2865, 174.7762];
  const initialZoom = 6;

  useEffect(() => {
    const fetchMapUsers = async () => {
      const token = localStorage.getItem('token');

      if (!token) {
        message.error('未找到登录 token，请先登录');
        return;
      }

      try {
        setLoading(true);

        const response = await fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'}/map/users`, {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const data = await response.json();
        console.log('map api response:', data);

        if (!response.ok) {
          throw new Error(data.detail || '获取地图数据失败');
        }

        const users = Array.isArray(data?.map_users) ? data.map_users : [];
        setMapUsers(users);

        const availableYears = [...new Set(users.map((item) => item.year).filter(Boolean))]
          .sort((a, b) => Number(b) - Number(a));

        if (availableYears.length > 0) {
          setSelectedYear(availableYears[0]);
        }
      } catch (error) {
        console.error('fetch map users error:', error);
        message.error(error.message || '地图数据加载失败');
      } finally {
        setLoading(false);
      }
    };

    fetchMapUsers();
  }, []);

  const availableYears = useMemo(() => {
    return [...new Set(mapUsers.map((item) => item.year).filter(Boolean))]
      .sort((a, b) => Number(b) - Number(a));
  }, [mapUsers]);

  const yearOptions = useMemo(() => {
    return availableYears.map((year) => ({
      value: year,
      label: year,
    }));
  }, [availableYears]);

  const regionOptions = useMemo(() => {
    const regions = [...new Set(
      mapUsers
        .map((item) => item.city || item.region || item.area)
        .filter(Boolean)
    )];

    return [
      { value: 'all', label: '全部' },
      ...regions.map((item) => ({
        value: item,
        label: item,
      })),
    ];
  }, [mapUsers]);

  const filteredPoints = useMemo(() => {
    return mapUsers.filter((item) => {
      const hasValidLatLng =
        item.latitude !== null &&
        item.longitude !== null &&
        item.latitude !== undefined &&
        item.longitude !== undefined;

      if (!hasValidLatLng) return false;

      const matchUserType =
        selectedUserType === 'all' || item.user_type === selectedUserType;

      const matchYear =
        !selectedYear || item.year === selectedYear;

      const matchMonth =
        selectedMonth === 'all' || item.month === selectedMonth;

      const currentRegion = item.city || item.region || item.area || '';
      const matchRegion =
        selectedRegion === 'all' || currentRegion === selectedRegion;

      const matchGender =
        selectedGender === 'all' || item.gender === selectedGender;

      const matchAgeRange =
        selectedAgeRange === 'all' || item.age_range === selectedAgeRange;

      const keyword = searchKeyword.trim().toLowerCase();
      const searchText = [
        item.uid,
        item.user_id,
        item.name,
        item.city,
        item.region,
        item.area,
        item.address,
        item.user_type,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      const matchSearch = !keyword || searchText.includes(keyword);

      return (
        matchUserType &&
        matchYear &&
        matchMonth &&
        matchRegion &&
        matchGender &&
        matchAgeRange &&
        matchSearch
      );
    });
  }, [
    mapUsers,
    selectedUserType,
    selectedYear,
    selectedMonth,
    selectedRegion,
    selectedGender,
    selectedAgeRange,
    searchKeyword,
  ]);

  const stats = useMemo(() => {
    return filteredPoints.reduce(
      (acc, p) => {
        if (p.gender === 'male') acc.maleCount += 1;
        if (p.gender === 'female') acc.femaleCount += 1;

        if (p.user_type === '注册用户') acc.registeredCount += 1;
        if (p.user_type === '已成功入金用户') acc.fundedCount += 1;
        if (p.user_type === '完成第一笔交易用户') acc.firstTradeCount += 1;
        if (p.user_type === '高净值用户') acc.hnwCount += 1;

        return acc;
      },
      {
        maleCount: 0,
        femaleCount: 0,
        registeredCount: 0,
        fundedCount: 0,
        firstTradeCount: 0,
        hnwCount: 0,
      }
    );
  }, [filteredPoints]);

  return (
    <div className="map-page">
      <div className="map-filters">
        <div className="map-filters-left">
          <div className="filter-item">
            <span className="filter-label">用户类型</span>
            <Select
              value={selectedUserType}
              size="middle"
              style={{ width: 180 }}
              options={userTypes}
              onChange={setSelectedUserType}
            />
          </div>

          <div className="filter-item">
            <span className="filter-label">年份</span>
            <Select
              value={selectedYear}
              size="middle"
              style={{ width: 100 }}
              options={yearOptions}
              onChange={setSelectedYear}
            />
          </div>

          <div className="filter-item">
            <span className="filter-label">月份</span>
            <Select
              value={selectedMonth}
              size="middle"
              style={{ width: 100 }}
              options={months}
              onChange={setSelectedMonth}
            />
          </div>

          <div className="filter-item">
            <span className="filter-label">地区</span>
            <Select
              value={selectedRegion}
              size="middle"
              style={{ width: 140 }}
              options={regionOptions}
              onChange={setSelectedRegion}
            />
          </div>

          <div className="filter-item">
            <span className="filter-label">性别</span>
            <Select
              value={selectedGender}
              size="middle"
              style={{ width: 100 }}
              options={genderOptions}
              onChange={setSelectedGender}
            />
          </div>

          <div className="filter-item">
            <span className="filter-label">年龄组</span>
            <Select
              value={selectedAgeRange}
              size="middle"
              style={{ width: 120 }}
              options={ageRangeOptions}
              onChange={setSelectedAgeRange}
            />
          </div>
        </div>

        <div className="map-filters-right">
          <span className="filter-label">搜索</span>
          <Input.Search
            placeholder="搜索用户ID / 姓名 / 地址"
            allowClear
            style={{ width: 260 }}
            onSearch={setSearchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            enterButton={
              <Button className="search-btn">
                <img
                  src="/search.png"
                  alt="search"
                  className="search-icon"
                />
              </Button>
            }
          />
        </div>
      </div>

      <Card className="map-card" bodyStyle={{ height: '100%', padding: 0 }}>
        <div className="map-wrapper">
          <div className="map-legend-top">
            <div className="legend-title">用户分布</div>

            <div className="legend-item">
              <img src="/laohu-logo.png" className="legend-img" alt="" />
              男性 - {stats.maleCount}
            </div>

            <div className="legend-item">
              <img src="/laohu-logo-female.png" className="legend-img" alt="" />
              女性 - {stats.femaleCount}
            </div>

            <div className="legend-divider"></div>

            <div className="legend-item">注册用户：{stats.registeredCount}</div>
            <div className="legend-item">已成功入金用户：{stats.fundedCount}</div>
            <div className="legend-item">完成第一笔交易用户：{stats.firstTradeCount}</div>
            <div className="legend-item">高净值用户：{stats.hnwCount}</div>
            <div className="legend-item">当前点位：{filteredPoints.length}</div>
          </div>

          <div className="map-floating-tools">
            <button
              className="map-fab"
              onClick={() => setShowInfoPanel((prev) => !prev)}
              title="更多信息"
            >
              ●
            </button>

            {showInfoPanel && (
              <div className="map-info-panel">
                <div className="map-info-panel-header">
                  <span>进一步数据</span>
                  <button
                    className="map-info-close"
                    onClick={() => setShowInfoPanel(false)}
                  >
                    ×
                  </button>
                </div>

                <div className="map-info-panel-body">
                  <div>总用户数：{mapUsers.length}</div>
                  <div>筛选后数量：{filteredPoints.length}</div>
                  <div>当前年份：{selectedYear || '-'}</div>
                  <div>当前月份：{selectedMonth === 'all' ? '全部' : selectedMonth}</div>
                </div>
              </div>
            )}
          </div>

          {loading ? (
            <div className="map-loading-box">
              <Spin size="large" />
            </div>
          ) : (
            <MapContainer
              center={initialCenter}
              zoom={initialZoom}
              className="leaflet-map"
            >
              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <ResetViewControl center={initialCenter} zoom={initialZoom} />
              <MarkerClusterLayer points={filteredPoints} />
            </MapContainer>
          )}
        </div>
      </Card>
    </div>
  );
}
