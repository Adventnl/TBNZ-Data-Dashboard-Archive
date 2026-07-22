import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
// import AnalysisLayout from './layouts/AnalysisLayout';
import MapPage from './pages/Map/MapPage';
import ClientsPage from './pages/Analysis/ClientsPage';
import ClientDetailPage from './pages/Analysis/ClientDetailPage';
import TradingPage from './pages/Analysis/TradingPage';
import AUCPage from './pages/Analysis/AUCPage';
import RankingsPage from './pages/Analysis/RankingsPage';
import ActivitiesPage from './pages/Activities/ActivitiesPage';
import LoginPage from './pages/Auth/Login/LoginPage';
import UploadingDataPage from './pages/setting/UploadingDataPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<AppLayout />}>
        <Route path="/uploading-data" element={<UploadingDataPage />} />
        <Route index element={<Navigate to="/analysis" replace />} />

          {/* Map */}
          <Route path="map" element={<MapPage />} />

          {/* Analysis with sub-navigation */}
          <Route path="analysis" element={<ClientsPage />} />
          <Route path="/analysis/clientDetail/:clientId" element={<ClientDetailPage />} />
          <Route path="analysis/trading" element={<TradingPage />} />
          <Route path="analysis/auc" element={<AUCPage />} />
          <Route path="analysis/rankings" element={<RankingsPage />} /> 

          {/* Activities */}
          <Route path="activities" element={<ActivitiesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
