import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Select, Statistic, Tag, Table, Space, Divider } from 'antd';
import {CheckCircleTwoTone } from '@ant-design/icons';

function PlanComparison() {
  const [savedPlans, setSavedPlans] = useState([]);
  const [selectedPlans, setSelectedPlans] = useState([]);
  const [comparisonData, setComparisonData] = useState(null);

  useEffect(() => {
    loadSavedPlans();
  }, []);

  const loadSavedPlans = async () => {
    try {
      const response = await fetch('/api/list_plans');
      const data = await response.json();
      setSavedPlans(data.plans);
    } catch (err) {
      console.error('Error loading plans:', err);
    }
  };

  const handleComparePlans = async () => {
    if (selectedPlans.length < 2) {
      return;
    }

    // Fetch full plan data for each selected plan
    const planDetails = await Promise.all(
      selectedPlans.map(planId => 
        fetch(`/api/load_plan/${planId}`).then(r => r.json())
      )
    );

    // Build comparison data structure
    const comparison = {
      plans: planDetails,
      metrics: calculateComparisonMetrics(planDetails)
    };

    setComparisonData(comparison);
  };

  const calculateComparisonMetrics = (plans) => {
    return plans.map(plan => {
      const allCourses = [];
      Object.keys(plan.plan).forEach(yearKey => {
        if (yearKey.startsWith('year_')) {
          allCourses.push(...(plan.plan[yearKey].fall || []));
          allCourses.push(...(plan.plan[yearKey].spring || []));
        }
      });

      return {
        planId: plan.id,
        planName: plan.name,
        totalCourses: allCourses.length,
        track: plan.track,
        // Add more metrics as needed
        uniqueCourses: new Set(allCourses).size
      };
    });
  };

  return (
    <div>
      <Card title="📊 Compare Your Plans">
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <label style={{ marginRight: '12px', fontWeight: 'bold' }}>
              Select Plans to Compare (2-3):
            </label>
            <Select
              mode="multiple"
              style={{ width: '100%', maxWidth: '600px' }}
              placeholder="Choose plans..."
              value={selectedPlans}
              onChange={setSelectedPlans}
              options={savedPlans.map(plan => ({
                value: plan.id,
                label: `${plan.name} (${plan.track})`
              }))}
            />
            <Button
              type="primary"
              icon={<CheckCircleTwoTone />}
              onClick={handleComparePlans}
              disabled={selectedPlans.length < 2}
              style={{ marginLeft: '12px' }}
            >
              Compare
            </Button>
          </div>

          {comparisonData && (
            <Row gutter={16}>
              {comparisonData.plans.map((plan, index) => (
                <Col span={24 / comparisonData.plans.length} key={plan.id}>
                  <Card
                    title={plan.name}
                    extra={<Tag color="blue">{plan.track}</Tag>}
                    size="small"
                  >
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Statistic
                        title="Total Courses"
                        value={comparisonData.metrics[index].totalCourses}
                      />

                      <Divider style={{ margin: '12px 0' }} />

                      {/* Course list by year */}
                      {[1, 2, 3, 4].map(year => {
                        const yearKey = `year_${year}`;
                        if (!plan.plan[yearKey]) return null;

                        return (
                          <div key={year} style={{ marginBottom: '16px' }}>
                            <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                              Year {year}
                            </div>
                            <div style={{ paddingLeft: '12px' }}>
                              {plan.plan[yearKey].fall && (
                                <div style={{ marginBottom: '8px' }}>
                                  <span style={{ fontWeight: '500' }}>Fall:</span>
                                  <div style={{ marginTop: '4px' }}>
                                    {plan.plan[yearKey].fall.map(c => (
                                      <Tag key={c} style={{ marginBottom: '4px' }}>
                                        {c}
                                      </Tag>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {plan.plan[yearKey].spring && (
                                <div>
                                  <span style={{ fontWeight: '500' }}>Spring:</span>
                                  <div style={{ marginTop: '4px' }}>
                                    {plan.plan[yearKey].spring.map(c => (
                                      <Tag key={c} style={{ marginBottom: '4px' }}>
                                        {c}
                                      </Tag>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Space>
      </Card>
    </div>
  );
}

export default PlanComparison;
