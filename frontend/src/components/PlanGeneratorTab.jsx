import React, { useState } from 'react';
import { Upload, Button, Select, Row, Col, Typography, message, Spin, Alert } from 'antd';
import { CheckCircleTwoTone } from '@ant-design/icons';
import PlanDisplay from './PlanDisplay';

const { Title, Text } = Typography;

const trackOptions = [
  { value: "general", label: "🤖 General CS (Broadest Focus)" },
  { value: "ai_ml", label: "🧠 Artificial Intelligence & ML" },
  { value: "security", label: "🔒 Cybersecurity" },
  { value: "systems", label: "⚙️ Systems & Networks" },
  { value: "game_dev", label: "🎮 Game Design & Development" },
];

function PlanGeneratorTab({ profile, isDataLoaded, setIsDataLoaded, generatedPlan, setGeneratedPlan, selectedTrack, setSelectedTrack }) {
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

  const handleUpload = async (file) => {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);
    
      try {
        console.log(`Uploading to: ${BACKEND_URL}/api/load_data`);
        
        const response = await fetch(`${BACKEND_URL}/api/load_data`, {
          method: 'POST',
          body: formData,
        });
    
        console.log(`Response status: ${response.status}`);
        
        if (!response.ok) {
          const err = await response.json();
          console.error(`Backend error: ${err.detail}`);
          setUploading(false);
          message.error(`Error: ${err.detail}`);
          return false;
        }
    
        const result = await response.json();
        console.log(`Success: ${result.message}`);
        
        setIsDataLoaded(true);
        message.success(result.message);
        setUploading(false);
        
      } catch (error) {
        console.error(`Caught error: ${error.message}`);
        message.error(`Error processing .pkl file: ${error.message}`);
        setIsDataLoaded(false);
        setUploading(false);
      }
      
      return false;
  };


  const handleGeneratePlan = async (planType) => {
      setLoading(true);
      setGeneratedPlan(null);
      
      const apiProfile = {
        name: profile.name || "Student",
        completed_courses: profile.completed_courses_input.split(',').map(c => c.trim().toUpperCase()).filter(Boolean),
        time_commitment: profile.time_commit || 40,
        preferred_difficulty: profile.difficulty || "moderate",
        career_goals: profile.career_goal || "",
        interests: profile.interests.split(',').map(i => i.trim()).filter(Boolean),
        current_gpa: profile.gpa || 3.5,
        learning_style: profile.learning_style || "Visual",
      };
      
      try {
        console.log(`Generating ${planType} plan...`);
        
        const params = new URLSearchParams({
          track: selectedTrack,
          plan_type: planType
        });
        
        const response = await fetch(`${BACKEND_URL}/api/generate_plan?${params}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(apiProfile),
        });
    
        console.log(`Response status: ${response.status}`);
        
        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || "Plan generation failed");
        }
    
        const planData = await response.json();
        setGeneratedPlan(planData);
        message.success(`🎉 Plan generated!`);
      } catch (error) {
        console.error(`Error: ${error.message}`);
        message.error(`Error generating plan: ${error.message}`);
      }
      setLoading(false);
  };


  return (
    <Spin spinning={loading} tip="Generating plan...">
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Title level={4}>1. Load Curriculum Data</Title>
          <Upload 
            beforeUpload={handleUpload} 
            maxCount={1} 
            showUploadList={false}
            accept=".pkl"
          >
            <Button icon={<CheckCircleTwoTone />} loading={uploading}>
              Upload .pkl File
            </Button>
          </Upload>
          {isDataLoaded && (
            <Alert 
              message="✅ Curriculum data loaded and ready." 
              type="success" 
              showIcon 
              style={{ marginTop: 16 }} 
            />
          )}
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            Backend URL: {BACKEND_URL}
          </Text>
        </Col>

        <Col span={24}>
          <Title level={4}>2. Select a Specialization</Title>
          <Select
            value={selectedTrack}
            options={trackOptions}
            onChange={setSelectedTrack}
            style={{ width: 300 }}
            disabled={!isDataLoaded}
          />
        </Col>

        <Col span={24}>
          <Title level={4}>3. Generate a Plan</Title>
          <Row gutter={16}>
            <Col span={8}>
              <Button 
                type="primary" 
                icon={<CheckCircleTwoTone />} 
                block 
                disabled={!isDataLoaded} 
                onClick={() => handleGeneratePlan('llm')}
              >
                AI-Optimized Plan
              </Button>
            </Col>
            <Col span={8}>
              <Button 
                icon={<CheckCircleTwoTone />} 
                block 
                disabled={!isDataLoaded} 
                onClick={() => handleGeneratePlan('simple')}
              >
                Smart Rule-Based Plan
              </Button>
            </Col>
            <Col span={8}>
              <Button 
                danger 
                icon={<CheckCircleTwoTone />} 
                block 
                onClick={() => setGeneratedPlan(null)}
              >
                Clear Plan
              </Button>
            </Col>
          </Row>
        </Col>
        
        {generatedPlan && (
          <Col span={24}>
            <PlanDisplay 
              plan={generatedPlan} 
              profile={profile}
              track={selectedTrack}
            />
          </Col>
        )}
      </Row>
    </Spin>
  );
}

export default PlanGeneratorTab;
