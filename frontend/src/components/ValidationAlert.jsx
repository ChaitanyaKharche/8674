import React from 'react';
import { Alert, Collapse, List, Tag } from 'antd';
import { WarningOutlined, CloseCircleOutlined } from '@ant-design/icons';

const { Panel } = Collapse;

function ValidationAlert({ validation, ...props }) {
  if (!validation || (validation.errors.length === 0 && validation.warnings.length === 0)) {
    return null;
  }

  const totalIssues = validation.errors.length + validation.warnings.length;

  return (
    <Alert
      type={validation.errors.length > 0 ? 'error' : 'warning'}
      message={`${totalIssues} issue${totalIssues > 1 ? 's' : ''} found in your plan`}
      description={
        <Collapse ghost>
          <Panel header="View Details" key="1">
            {validation.errors.length > 0 && (
              <>
                <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                  <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: '8px' }} />
                  Errors ({validation.errors.length})
                </div>
                <List
                  size="small"
                  dataSource={validation.errors}
                  renderItem={error => (
                    <List.Item>
                      <Tag color="error">{error.type}</Tag>
                      {error.message}
                    </List.Item>
                  )}
                />
              </>
            )}
            
            {validation.warnings.length > 0 && (
              <>
                <div style={{ fontWeight: 'bold', marginTop: '16px', marginBottom: '8px' }}>
                  <WarningOutlined style={{ color: '#faad14', marginRight: '8px' }} />
                  Warnings ({validation.warnings.length})
                </div>
                <List
                  size="small"
                  dataSource={validation.warnings}
                  renderItem={warning => (
                    <List.Item>
                      <Tag color="warning">{warning.type}</Tag>
                      {warning.message}
                    </List.Item>
                  )}
                />
              </>
            )}
          </Panel>
        </Collapse>
      }
      {...props}
    />
  );
}

export default ValidationAlert;
