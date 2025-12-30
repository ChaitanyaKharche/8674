import React from 'react';
import Plot from 'react-plotly.js';

// This component replaces interactive_visualizer.create_interactive_plot
function InteractiveGraph({ graphData }) {
  
  // Transform the API data into Plotly.js format
  const edgeTraces = graphData.edges.map(edge => ({
    x: edge.x_coords,
    y: edge.y_coords,
    mode: 'lines',
    line: {
      width: edge.is_critical ? 3 : 1,
      color: edge.is_critical ? 'red' : '#888',
    },
    hoverinfo: 'none',
  }));

  const nodeTrace = {
    x: graphData.nodes.map(n => n.x),
    y: graphData.nodes.map(n => n.y),
    text: graphData.nodes.map(n => n.label), // Text on the node
    hovertext: graphData.nodes.map(n => 
      `<b>${n.id}: ${n.name}</b><br>Complexity: ${n.complexity}<br>Blocking: ${n.blocking}`
    ),
    mode: 'markers+text',
    textposition: 'top center',
    textfont: { size: 9 },
    hoverinfo: 'text',
    marker: {
      showscale: true,
      colorscale: 'Viridis',
      size: graphData.nodes.map(n => n.size),
      color: graphData.nodes.map(n => n.complexity),
      colorbar: {
        thickness: 15,
        title: { text: "Complexity", side: "right" },
        xanchor: 'left',
      },
    },
  };

  const layout = {
    title: 'Interactive Curriculum Map',
    showlegend: false,
    hovermode: 'closest',
    margin: { b: 0, l: 0, r: 0, t: 40 },
    plot_bgcolor: 'white',
    height: 800,
    xaxis: { showgrid: false, zeroline: false, showticklabels: false },
    yaxis: { showgrid: false, zeroline: false, showticklabels: false },
  };

  return (
    <Plot
      data={[...edgeTraces, nodeTrace]}
      layout={layout}
      style={{ width: '100%', height: '800px' }}
      useResizeHandler
    />
  );
}

export default InteractiveGraph;