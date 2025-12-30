import React, { useState } from 'react';
import { Layout, Tabs } from 'antd';
import 'antd/dist/reset.css';
import PlanGeneratorTab from './components/PlanGeneratorTab';
import CurriculumMapTab from './components/CurriculumMapTab';
import AnalyticsTab from './components/AnalyticsTab';
import StudentProfileSidebar from './components/StudentProfileSidebar';
import InteractivePlanEditor from './components/InteractivePlanEditor';
import PlanVariationSelector from './components/PlanVariationSelector';
import PlanComparison from './components/PlanComparison';

const { Header, Content, Sider } = Layout;

function App() {
  const [profile, setProfile] = useState({
    name: 'John, son of Jane',
    gpa: 3.0,
    career_goal: ' ',
    interests: ' ',
    learning_style: 'Visual',
    time_commit: 40,
    difficulty: 'moderate',
    completed_courses_input: ' ',
  });
  
  const [isDataLoaded, setIsDataLoaded] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState(null);
  const [selectedTrack, setSelectedTrack] = useState('general');
  const [activeTab, setActiveTab] = useState('1');

  const handleSavePlan = async (plan) => {
    const response = await fetch('/api/save_plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan,
        profile,
        track: selectedTrack
      })
    });
    return response.json();
  };

  const handleVariationSelected = (variation) => {
    console.log('Selected variation:', variation);
  };

  const tabs = [
    {
      key: '1',
      label: '🎯 Plan Generator',
      children: (
        <PlanGeneratorTab
          profile={profile}
          isDataLoaded={isDataLoaded}
          setIsDataLoaded={setIsDataLoaded}
          generatedPlan={generatedPlan}
          setGeneratedPlan={setGeneratedPlan}
          selectedTrack={selectedTrack}
          setSelectedTrack={setSelectedTrack}
        />
      )
    },
    {
      key: '2',
      label: '✏️ Interactive Planner',
      children: generatedPlan ? (
        <InteractivePlanEditor
          initialPlan={generatedPlan.pathway}
          profile={profile}
          track={selectedTrack}
          onSave={handleSavePlan}
        />
      ) : (
        <div style={{ textAlign: 'center', padding: '60px' }}>
          Generate a plan first to start editing
        </div>
      )
    },

  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={300} theme="light">
        <StudentProfileSidebar 
          profile={profile} 
          setProfile={setProfile} 
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px' }}>
          <h1>🧑‍🎓 Next-Gen Curriculum Optimizer</h1>
        </Header>
        <Content style={{ padding: '24px' }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabs}
            size="large"
          />
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
