import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

interface DashboardProps {
  data: {
    summary: string;
    findings: string[];
    charts: any[];
    recommendations: string[];
  };
}

export default function Dashboard({ data }: DashboardProps) {
  return (
    <div className="dashboard-container">
      <div className="card summary-card">
        <h3>Executive Summary</h3>
        <p>{data.summary}</p>
      </div>

      <div className="dashboard-grid">
        <div className="card findings-card">
          <h3>Key Findings</h3>
          <ul>
            {data.findings.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
        
        <div className="card recs-card">
          <h3>Recommendations</h3>
          <ul>
            {data.recommendations.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      </div>

      {data.charts && data.charts.length > 0 && (
        <div className="charts-section">
          <h3>Visualizations</h3>
          <div className="charts-grid">
            {data.charts.map((chart, i) => (
              <div className="card chart-card" key={i}>
                <h4>{chart.title}</h4>
                <div style={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer>
                    {chart.type === 'line' ? (
                      <LineChart data={chart.labels.map((l: string, idx: number) => {
                        const point: any = { name: l };
                        chart.datasets.forEach((ds: any) => {
                          point[ds.label] = ds.data[idx];
                        });
                        return point;
                      })}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        {chart.datasets.map((ds: any, dsi: number) => (
                          <Line key={dsi} type="monotone" dataKey={ds.label} stroke={`hsl(${dsi * 45 + 200}, 70%, 50%)`} />
                        ))}
                      </LineChart>
                    ) : (
                      <BarChart data={chart.labels.map((l: string, idx: number) => {
                        const point: any = { name: l };
                        chart.datasets.forEach((ds: any) => {
                          point[ds.label] = ds.data[idx];
                        });
                        return point;
                      })}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        {chart.datasets.map((ds: any, dsi: number) => (
                          <Bar key={dsi} dataKey={ds.label} fill={`hsl(${dsi * 45 + 200}, 70%, 50%)`} />
                        ))}
                      </BarChart>
                    )}
                  </ResponsiveContainer>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
