import React, { useState, useEffect } from 'react';
import { Row, Col, Typography, Statistic, Card, Button, List, Alert, Tag } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

function PlanDisplay({ plan, profile, track }) {
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
  const [courses, setCourses] = useState({});
  
  // Fetch course data on mount
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/courses`);
        if (!response.ok) throw new Error('Failed to fetch courses');
        const data = await response.json();
        setCourses(data.courses || {});
      } catch (err) {
        console.error('Error fetching courses:', err);
      }
    };
    fetchCourses();
  }, [BACKEND_URL]);

  const planData = plan?.pathway || plan;
  
  if (!planData) {
    return <Alert message="No plan data available" type="error" />;
  }

  const getCourseInfo = (courseId) => {
    return courses[courseId] || { name: 'Unknown', maxCredits: 4 };
  };

  const handleExport = async (format) => {
    let url = `${BACKEND_URL}/api/export_yaml`;
    let filename = `curriculum_plan_${profile.name}.yaml`;
    
    const apiProfile = {
      ...profile,
      completed_courses: profile.completed_courses_input.split(',').map(c => c.trim().toUpperCase()).filter(Boolean),
      interests: profile.interests.split(',').map(i => i.trim()).filter(Boolean),
    };

    const requestBody = {
      profile: apiProfile,
      track: track,
      plan: planData,
    };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const href = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = href;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(href);
    } catch (err) {
      console.error('Export error', err);
    }
  };

  return (
    <Card>
      <Title level={4}>📚 Optimized Degree Plan</Title>
      
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}><Text>{planData.reasoning}</Text></Col>
        <Col span={12}>
          <Statistic 
            title="Total Complexity" 
            value={planData.complexity_analysis?.total_complexity || 0} 
            precision={0}
          />
        </Col>
      </Row>
      
      <Row gutter={[16, 16]}>
        {[1, 2, 3, 4].map(year => {
          const yearKey = `year_${year}`;
          const yearData = planData[yearKey];
          
          if (!yearData) return null;
          
          return (
            <Col xs={24} key={year}>
              <Card title={`Year ${year}`} size="small">
                <Row gutter={16}>
                    {['fall', 'spring'].map(sem => {
                      const courseIds = yearData[sem] || [];
                      return (
                        <Col xs={24} md={12} key={sem}>
                          <Card title={`${sem.toUpperCase()}`} size="small" style={{ background: '#fafafa' }}>
                            {courseIds.length === 0 ? (
                              <Text type="secondary">No courses scheduled</Text>
                            ) : (
                              <List
                                dataSource={courseIds}
                                renderItem={courseId => {
                                  const courseInfo = getCourseInfo(courseId);
                                  return (
                                    <List.Item key={courseId}>
                                      <div style={{ width: '100%' }}>
                                        <Tag color="blue">{courseId}</Tag>
                                        <Text strong>{courseInfo.name}</Text>
                                        <Text type="secondary"> ({courseInfo.maxCredits} credits)</Text>
                                      </div>
                                    </List.Item>
                                  );
                                }}
                              />
                            )}
                          </Card>
                        </Col>
                      );
                    })}
                </Row>
              </Card>
            </Col>
          );
        })}
      </Row>
      
      <Button 
        icon={<DownloadOutlined />} 
        onClick={() => handleExport('yaml')}
        style={{ marginTop: 20 }}
      >
        Export as YAML
      </Button>
    </Card>
  );
}

export default PlanDisplay;
