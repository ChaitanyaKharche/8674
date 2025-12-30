import React, { useState, useEffect } from 'react';
import { Card, Radio, Table, Tag, Button, Space, Collapse, Statistic, Row, Col, Spin, message } from 'antd';
import { CheckCircleTwoTone } from '@ant-design/icons';

const { Panel } = Collapse;

function PlanVariationSelector({ track, onSelectVariation }) {
  const [variations, setVariations] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [selectedVariationId, setSelectedVariationId] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (track) {
      loadVariations();
    }
  }, [track]);

  const loadVariations = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/generate_variations?track=${track}&max_variations=5`, {
        method: 'POST'
      });
      const data = await response.json();
      setVariations(data.variations);
      setAnalytics(data.analytics);
      
      // Auto-select first variation
      if (data.variations.length > 0) {
        setSelectedVariationId(data.variations.id);
      }
    } catch (err) {
      message.error('Error loading plan variations');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectVariation = (variationId) => {
    setSelectedVariationId(variationId);
    const variation = variations.find(v => v.id === variationId);
    if (variation && onSelectVariation) {
      onSelectVariation(variation);
    }
  };

  const handleGenerateFromVariation = (variation) => {
    // Trigger plan generation with this specific course combination
    message.success(`Generating plan from ${variation.name}...`);
    onSelectVariation(variation);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Spin size="large" />
        <p>Analyzing all possible degree paths...</p>
      </div>
    );
  }

  return (
    <div>
      <Card
        title={`📊 ${track.replace('_', ' ').toUpperCase()} Track - Plan Variations`}
        extra={
          <Button onClick={loadVariations} size="small">
            Refresh
          </Button>
        }
      >
        {analytics && (
          <Row gutter={16} style={{ marginBottom: '20px' }}>
            <Col span={6}>
              <Statistic 
                title="Total Valid Combinations" 
                value={analytics.total_combinations} 
                prefix={<CheckCircleTwoTone />}
              />
            </Col>
            <Col span={6}>
              <Statistic 
                title="Median Complexity" 
                value={analytics.median_complexity?.toFixed(1) || 'N/A'} 
              />
            </Col>
            <Col span={6}>
              <Statistic 
                title="Min Complexity" 
                value={analytics.min_complexity?.toFixed(1) || 'N/A'} 
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={6}>
              <Statistic 
                title="Max Complexity" 
                value={analytics.max_complexity?.toFixed(1) || 'N/A'} 
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Col>
          </Row>
        )}

        <p style={{ marginBottom: '16px', color: '#666' }}>
          Based on your track requirements, there are <strong>{analytics?.total_combinations || 0}</strong> valid 
          ways to complete your degree. Here are the top variations:
        </p>

        <Radio.Group
          value={selectedVariationId}
          onChange={(e) => handleSelectVariation(e.target.value)}
          style={{ width: '100%' }}
        >
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {variations.map((variation, index) => (
              <Card
                key={variation.id}
                size="small"
                hoverable
                style={{
                  border: selectedVariationId === variation.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                  background: selectedVariationId === variation.id ? '#f0f5ff' : 'white'
                }}
              >
                <Radio value={variation.id} style={{ width: '100%' }}>
                  <div style={{ marginLeft: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong style={{ fontSize: '16px' }}>{variation.name}</strong>
                      <Space>
                        <Tag color={
                          variation.estimated_complexity < 200 ? 'green' :
                          variation.estimated_complexity < 250 ? 'orange' : 'red'
                        }>
                          Complexity: {variation.estimated_complexity.toFixed(0)}
                        </Tag>
                        <Tag color="blue">{variation.courses.length} courses</Tag>
                      </Space>
                    </div>

                    <Collapse ghost style={{ marginTop: '12px' }}>
                      <Panel header="View Course List" key="1">
                        <div style={{ 
                          display: 'grid', 
                          gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
                          gap: '8px'
                        }}>
                          {variation.courses.sort().map(courseId => (
                            <Tag key={courseId} color="default">
                              {courseId}
                            </Tag>
                          ))}
                        </div>
                      </Panel>
                    </Collapse>

                    {selectedVariationId === variation.id && (
                      <Button
                        type="primary"
                        icon={<CheckCircleTwoTone />}
                        onClick={() => handleGenerateFromVariation(variation)}
                        style={{ marginTop: '12px' }}
                      >
                        Generate Plan from This Variation
                      </Button>
                    )}
                  </div>
                </Radio>
              </Card>
            ))}
          </Space>
        </Radio.Group>
      </Card>

      {/* Elective Choice Frequency Analysis */}
      {analytics?.choice_scores && (
        <Card
          title="📈 Elective Popularity Analysis"
          style={{ marginTop: '20px' }}
        >
          <p style={{ marginBottom: '16px', color: '#666' }}>
            Shows how often each elective appears across all valid degree combinations.
            Higher percentages = more common/recommended courses.
          </p>
          <ElectiveFrequencyTable choiceScores={analytics.choice_scores} />
        </Card>
      )}
    </div>
  );
}

// Sub-component for elective frequency table
function ElectiveFrequencyTable({ choiceScores }) {
  // Convert choice_scores object to array for table
  const data = Object.entries(choiceScores || {})
    .map(([courseId, score]) => ({
      key: courseId,
      courseId,
      frequency: (score * 100).toFixed(1),
      rawScore: score,
      recommendation: score > 0.7 ? 'Highly Recommended' : 
                      score > 0.4 ? 'Commonly Chosen' : 
                      'Less Common'
    }))
    .sort((a, b) => b.rawScore - a.rawScore);

  const columns = [
    {
      title: 'Course',
      dataIndex: 'courseId',
      key: 'courseId',
      render: (courseId) => <Tag color="blue">{courseId}</Tag>
    },
    {
      title: 'Frequency',
      dataIndex: 'frequency',
      key: 'frequency',
      render: (freq) => `${freq}%`,
      sorter: (a, b) => parseFloat(a.frequency) - parseFloat(b.frequency),
      defaultSortOrder: 'descend'
    },
    {
      title: 'Recommendation',
      dataIndex: 'recommendation',
      key: 'recommendation',
      render: (rec) => {
        const color = rec === 'Highly Recommended' ? 'green' :
                      rec === 'Commonly Chosen' ? 'blue' : 'default';
        return <Tag color={color}>{rec}</Tag>;
      },
      filters: [
        { text: 'Highly Recommended', value: 'Highly Recommended' },
        { text: 'Commonly Chosen', value: 'Commonly Chosen' },
        { text: 'Less Common', value: 'Less Common' }
      ],
      onFilter: (value, record) => record.recommendation === value
    }
  ];

  return (
    <Table
      dataSource={data}
      columns={columns}
      size="small"
      pagination={{ pageSize: 10 }}
    />
  );
}

export default PlanVariationSelector;
