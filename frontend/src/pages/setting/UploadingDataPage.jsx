import React, { useRef, useState } from 'react';
import {
  CloudUploadOutlined,
  FileTextOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import './UploadingDataPage.css';

const mockHistory = [
  {
    id: 1,
    fileName: 'Q4_Client_Reconciliation_Final.xlsx',
    tag: 'INSTITUTIONAL TIER',
    period: '90 Days',
    lastLoad: 'Oct 24, 2023\n14:20',
    records: '14,202',
    status: 'success',
    statusLabel: 'SUCCESS',
  },
  {
    id: 2,
    fileName: 'Real_Time_Market_Mapping.csv',
    tag: 'HIGH FREQUENCY FEED',
    period: '1 Day',
    lastLoad: 'Oct 25, 2023\n09:45',
    records: '2,490',
    status: 'progress',
    statusLabel: 'IN PROGRESS',
  },
  {
    id: 3,
    fileName: 'Global_Wealth_Index_Dump.tsv',
    tag: 'INDEX DATA',
    period: '30 Days',
    lastLoad: 'Oct 22, 2023\n18:10',
    records: '0',
    status: 'failed',
    statusLabel: 'FAILED',
  },
];

export default function UploadingDataPage() {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleChooseFile = () => {
    inputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  return (
    <div className="data-ingest-page">
      <div className="ingest-card">
        <div className="ingest-card-header">
          <div>
            <h2 className="ingest-title">Ingest Financial Datasets</h2>
            <p className="ingest-subtitle">
              Synchronize your institutional records with the Obsidian Tiger core
              engine.
            </p>
          </div>

          <button className="upload-icon-btn" type="button">
            <CloudUploadOutlined />
          </button>
        </div>

        <div
          className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="upload-dropzone-inner">
            <div className="upload-file-icon">
              <FileTextOutlined />
            </div>

            <div className="upload-main-title">
              {selectedFile ? selectedFile.name : 'Upload or Drag File'}
            </div>

            <div className="upload-desc">
              Supported formats: xlsx, csv, tsv (Max 50MB)
            </div>

            <button
              className="upload-primary-btn"
              type="button"
              onClick={handleChooseFile}
            >
              选择数据源
            </button>

            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.csv,.tsv"
              className="hidden-file-input"
              onChange={handleFileChange}
            />
          </div>
        </div>
      </div>

      <div className="history-section">
        <div className="history-header">
          <div className="history-title-wrap">
            <span className="history-dot" />
            <span className="history-title">TRANSACTION HISTORY</span>
          </div>

        </div>

        <div className="history-table-card">
          <table className="history-table">
            <thead>
              <tr>
                <th>DATASET / FILE</th>
                <th>DATA LOADING PERIOD (DAYS)</th>
                <th>LAST LOAD TIME</th>
                <th>NUMBER OF RECORDS LOADED</th>
                <th>STATUS</th>
              </tr>
            </thead>

            <tbody>
              {mockHistory.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className="file-name">{item.fileName}</div>
                    <div className="file-tag">{item.tag}</div>
                  </td>

                  <td>{item.period}</td>

                  <td>
                    {item.lastLoad.split('\n').map((line) => (
                      <div key={line}>{line}</div>
                    ))}
                  </td>

                  <td>{item.records}</td>

                  <td>
                    <span className={`status-badge status-${item.status}`}>
                      {item.statusLabel}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}