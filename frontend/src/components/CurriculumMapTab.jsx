import React, { useState, useEffect } from 'react';
import { Spin, Alert, Collapse } from 'antd';
import InteractiveGraph from './InteractiveGraph'; // The new component

const { Panel } = Collapse;

function CurriculumMapTab({ isDataLoaded }) {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Replaces the st.plotly_chart logic
  useEffect(() => {
    if (isDataLoaded) {
      setLoading(true);
      setError(null);
      fetch('/api/graph_data')
        .then(res => {
          if (!res.ok) throw new Error("Failed to fetch graph data");
          return res.json();
        })
        .then(data => {
          setGraphData(data);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message);
          setLoading(false);
        });
    }
  }, [isDataLoaded]);

  if (!isDataLoaded) {
    return <Alert message="Please load curriculum data in the Plan Generator tab first." type="info" />;
  }

  if (loading) {
    return <Spin tip="Loading graph..." />;
  }
  
  if (error) {
    return <Alert message={`Error: ${error}`} type="error" />;
  }

  return (
    <div>
      {graphData?.critical_path && (
        <Alert
          message={`Global Critical Path (${graphData.critical_path.length} courses): ${graphData.critical_path.slice(0, 7).join(' → ')}...`}
          type="info"
          style={{ marginBottom: 16 }}
        />
      )}
      
      {graphData && <InteractiveGraph graphData={graphData} />}
      
      <Collapse style={{ marginTop: 16 }}>
        <Panel header="📖 How to Read This Graph" key="1">
          <p><strong>Node (Circle) Size</strong>: Blocking factor - larger circles block more future courses</p>
          <p><strong>Node Color</strong>: Complexity score - darker = more complex</p>
          <p><strong>Lines</strong>: Prerequisite relationships</p>
          <p><strong>Red Path</strong>: Critical path (longest chain)</p>
          <p><strong>Hover over nodes</strong>: See detailed metrics for each course</p>
        </Panel>
      </Collapse>
    </div>
  );
}

export default CurriculumMapTab;