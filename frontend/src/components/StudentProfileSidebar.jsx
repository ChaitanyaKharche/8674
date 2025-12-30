import React from 'react';
import { Input, Slider, Select, InputNumber, Typography, Space, Alert } from 'antd';

const { Title, Text } = Typography;
const { TextArea } = Input;

// Replaces the st.sidebar
function StudentProfileSidebar({ profile, setProfile }) {

  const handleChange = (key, value) => {
    setProfile(prev => ({ ...prev, [key]: value }));
  };
  
  const getProfileImpact = () => {
    let loadInfo, diffInfo;
    if (profile.time_commit < 20) loadInfo = "🕒 Part-time load (3 courses/semester)";
    else if (profile.time_commit >= 40) loadInfo = "🔥 Intensive load (up to 5 courses/semester)";
    else loadInfo = "📚 Standard load (4 courses/semester)";

    if (profile.difficulty === "easy") diffInfo = "😌 Focuses on foundational courses";
    else if (profile.difficulty === "challenging") diffInfo = "🚀 Includes advanced/specialized courses";
    else diffInfo = "⚖️ Balanced difficulty progression";

    return (
      <>
        <Alert message={loadInfo} type="info" showIcon style={{ marginBottom: 8 }} />
        <Alert message={diffInfo} type="info" showIcon />
      </>
    );
  };

  return (
    <Space direction="vertical" style={{ padding: 24, width: '100%' }}>
      <Title level={4}>Student Profile</Title>
      
      <Text>Name</Text>
      <Input value={profile.name} onChange={(e) => handleChange('name', e.target.value)} />
      
      <Text>GPA</Text>
      <Slider min={0.0} max={4.0} step={0.1} value={profile.gpa} onChange={(val) => handleChange('gpa', val)} />
      
      <Text>Career Goal</Text>
      <TextArea value={profile.career_goal} onChange={(e) => handleChange('career_goal', e.target.value)} />
      
      <Text>Interests (comma-separated)</Text>
      <Input value={profile.interests} onChange={(e) => handleChange('interests', e.target.value)} />
      
      <Text>Learning Style</Text>
      <Select value={profile.learning_style} style={{ width: '100%' }} onChange={(val) => handleChange('learning_style', val)}>
        <Select.Option value="Visual">Visual</Select.Option>
        <Select.Option value="Hands-on">Hands-on</Select.Option>
        <Select.Option value="Auditory">Auditory</Select.Option>
      </Select>
      
      <Text>Weekly Study Hours</Text>
      <InputNumber min={10} max={60} step={5} value={profile.time_commit} onChange={(val) => handleChange('time_commit', val)} />

      <Text>Preferred Difficulty</Text>
      <Select value={profile.difficulty} style={{ width: '100%' }} onChange={(val) => handleChange('difficulty', val)}>
        <Select.Option value="easy">Easy</Select.Option>
        <Select.Option value="moderate">Moderate</Select.Option>
        <Select.Option value="challenging">Challenging</Select.Option>
      </Select>

      <Text>Completed Courses (comma-separated)</Text>
      <TextArea value={profile.completed_courses_input} onChange={(e) => handleChange('completed_courses_input', e.target.value)} />

      <Title level={5}>Profile Impact</Title>
      {getProfileImpact()}
    </Space>
  );
}

export default StudentProfileSidebar;