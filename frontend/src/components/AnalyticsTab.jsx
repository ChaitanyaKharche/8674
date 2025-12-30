import React, { useState, useEffect } from 'react';
import { Spin, Alert, Row, Col, Statistic, List, Progress } from 'antd';

function AnalyticsTab({ isDataLoaded, generatedPlan }) {
  const [analytics, setAnalytics] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isDataLoaded) {
      setLoading(true);
      setError(null);
      fetch('/api/analytics_dashboard')
        .then(res => res.json())
        .then(data => {
          setAnalytics(data);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message);
          setLoading(false);
        });
    }
  }, [isDataLoaded]);

  useEffect(() => {
    if (isDataLoaded && generatedPlan) {
      fetch('/api/compare_metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(generatedPlan),
      })
        .then(res => res.json())
        .then(data => setComparison(data))
        .catch(err => console.error("Comparison error:", err));
    }
  }, [isDataLoaded, generatedPlan]);

  if (!isDataLoaded) {
    return <Alert message="Please load curriculum data in the Plan Generator tab first." type="info" />;
  }

  if (loading) {
    return <Spin tip="Loading analytics..." />;
  }

  if (error) {
    return <Alert message={`Error: ${error}`} type="error" />;
  }

  return (
    <Row gutter={[16, 24]}>
      <Col span={12}>
        <Statistic title="Total Courses" value={analytics?.most_complex?.length + analytics?.bottlenecks?.length} />
      </Col>
      {/* Add more global stats as needed */}
      
      <Col span={12}>
        <List
          header={<div>Most Complex Courses</div>}
          bordered
          dataSource={analytics?.most_complex}
          renderItem={item => (
            <List.Item>
              <List.Item.Meta title={`${item.course}: ${item.name}`} />
              <Progress percent={item.complexity} size="small" />
            </List.Item>
          )}
        />
      </Col>
      <Col span={12}>
        <List
          header={<div>Bottleneck Courses (High Blocking)</div>}
          bordered
          dataSource={analytics?.bottlenecks}
          renderItem={item => (
            <List.Item>
              <List.Item.Meta title={`${item.course}: ${item.name}`} />
              <div>Blocks {item.blocking} courses</div>
            </List.Item>
          )}
        />
      </Col>

      {comparison && (
        <Col span={24}>
          <h3>Metric System Comparison</h3>
          <Row gutter={16}>
            <Col span={12}>
              <Statistic title="Critical Path Match" value={comparison.critical_path_match ? '✅ Yes' : '❌ No'} />
              <p>Global: {comparison.global_critical?.join(' → ')}</p>
              <p>Plan: {comparison.plan_critical?.join(' → ')}</p>
            </Col>
            <Col span={12}>
              <Statistic title="Major Metric Differences (>50%)" value={comparison.major_differences?.length} />
            </Col>
          </Row>
        </Col>
      )}
    </Row>
  );
}

export default AnalyticsTab;