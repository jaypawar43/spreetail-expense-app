import { useState, useCallback } from 'react';
import Layout from './components/Layout';
import FileUpload from './components/FileUpload';
import ImportReport from './components/ImportReport';
import Dashboard from './components/Dashboard';
import Balances from './components/Balances';
import PersonManager from './components/PersonManager';

/**
 * App — Main application with step-by-step tab flow.
 * Upload CSV → See Import Report → View Dashboard → Check Balances
 */
export default function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [importSession, setImportSession] = useState(null);
  const [anomalyCount, setAnomalyCount] = useState(0);

  const handleUploadComplete = useCallback((session) => {
    setImportSession(session);
    setAnomalyCount(session.anomaly_count || 0);
    setActiveTab('report');
  }, []);

  const tabs = [
    { id: 'upload', label: 'Upload CSV', icon: '📤' },
    { id: 'report', label: 'Import Report', icon: '📋', badge: anomalyCount },
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'balances', label: 'Balances', icon: '💰' },
    { id: 'persons', label: 'People', icon: '👥' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'upload':
        return <FileUpload onUploadComplete={handleUploadComplete} />;
      case 'report':
        return <ImportReport session={importSession} />;
      case 'dashboard':
        return <Dashboard sessionId={importSession?.id} />;
      case 'balances':
        return <Balances sessionId={importSession?.id} />;
      case 'persons':
        return <PersonManager />;
      default:
        return <FileUpload onUploadComplete={handleUploadComplete} />;
    }
  };

  return (
    <Layout
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
    >
      {renderContent()}
    </Layout>
  );
}
