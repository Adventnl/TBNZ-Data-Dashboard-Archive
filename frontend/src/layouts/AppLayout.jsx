import { Layout, Menu, Avatar, Typography, Breadcrumb } from 'antd';
import React, { useState } from 'react';
import {
  GlobalOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  BellOutlined,
  SettingOutlined, 
  CloseOutlined, 
  InboxOutlined, 
  UploadOutlined, 
  SyncOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import './AppLayout.css';

const { Sider, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  {
    key: '/map',
    icon: <GlobalOutlined />,
    label: '地图 (Map)',
  },
  {
    key: '/analysis',
    icon: <BarChartOutlined />,
    label: '综合分析 (Whole)',
  },
  {
    key: '/activities',
    icon: <ThunderboltOutlined />,
    label: '活动分析 (Activities)',
  },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  const [showSettingsPanel, setShowSettingsPanel] = useState(false);

  const currentPath = location.pathname;

  const selectedItem = menuItems.find((item) =>
    currentPath.startsWith(item.key)
  );

  const selectedKey = selectedItem ? selectedItem.key : '/map';

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  const getBreadcrumbItems = () => {
    if (currentPath.startsWith('/map')) {
      return ['地图', '地图总览'];
    }
    if (currentPath.startsWith('/analysis')) {
      return ['综合分析', '综合总览'];
    }
    if (currentPath.startsWith('/activities')) {
      return ['活动分析', '活动总览'];
    }
    return ['页面'];
  };

  return (
    <Layout className="app-layout">
      <Sider
        width={240}
        className="app-sidebar"
        theme="light"
      >
        <div className="sidebar-logo">
          <div className="logo-icon">
            <img src="/laohu-logo.png" alt="logo" className="logo-img" />
          </div>
          <div className="logo-text">
            <Text strong style={{ fontSize: 16, lineHeight: 2, paddingLeft: 12 }}>
              Tiger Brokers
            </Text>
          </div>
        </div>

        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
          className="sidebar-menu"
        />

        <div className="sidebar-user">
          <Avatar size={36} style={{ backgroundColor: '#F0F0F0', color: '#666' }}>
          </Avatar>
          <div className="user-info">
            <Text strong style={{ fontSize: 13 }}>xxx</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>xxxx</Text>
          </div>
            <button className="sidebar-setting-btn" type="button" onClick={() => setShowSettingsPanel(true)}>
              <SettingOutlined className="sidebar-setting-icon" />
            </button>
              {/* 右侧弹出面板 */}
              <div className={`settings-panel ${showSettingsPanel ? 'open' : ''}`}>
                <div className="settings-panel-header">
                  <div>
                    <div className="settings-panel-title">数据管理</div>
                    <div className="settings-panel-subtitle">选择你要执行的操作</div>
                  </div>

                  <button
                    className="settings-close-btn"
                    type="button"
                    onClick={() => setShowSettingsPanel(false)}
                  >
                    <CloseOutlined />
                  </button>
                </div>

                <div className="settings-panel-body">
                  <button className="settings-menu-item" type="button" onClick={() => navigate('/uploading-data')}> 
                    <InboxOutlined className="settings-menu-icon" />
                    <div className="settings-menu-text">
                      <div className="settings-menu-title">导入数据</div>
                      <div className="settings-menu-desc">上传客户、交易或活动数据文件</div>
                    </div>
                  </button>

                  <button className="settings-menu-item" type="button">
                    <SyncOutlined className="settings-menu-icon" />
                    <div className="settings-menu-text">
                      <div className="settings-menu-title">同步记录</div>
                      <div className="settings-menu-desc">查看最近一次数据同步状态</div>
                    </div>
                  </button>

                  <div className="settings-panel-footer">
                    <button
                      className="logout-btn"
                      type="button"
                      onClick={() => {
                        console.log('logout');
                        // TODO: 这里以后接 logout 逻辑
                      }}
                    >
                      退出登录
                    </button>
                  </div>
                </div>
              </div>
          </div>
      </Sider>

      <Layout className="app-main">
        <div className="app-top-section">
          <div className="app-top-left">
            <Breadcrumb
              items={getBreadcrumbItems().map((item) => ({ title: item }))}
            />
          </div>

          <div className="app-top-right">
            <BellOutlined className="top-notification-icon" />
          </div>
        </div>

        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}