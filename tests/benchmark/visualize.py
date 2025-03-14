"""
Visualization module for Cloudflare bypass benchmark results.
"""

import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime

def create_benchmark_dashboard(results_file: str, output_file: str = None) -> None:
    """Create an HTML dashboard from benchmark results."""
    with open(results_file) as f:
        results = json.load(f)
    
    # Convert results to DataFrame
    df = pd.DataFrame(results)
    
    # Create figure with secondary y-axis
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Success Rate by Test',
            'Response Time Distribution',
            'Resource Usage',
            'Success Rate Over Time'
        ),
        specs=[
            [{"type": "bar"}, {"type": "box"}],
            [{"type": "scatter"}, {"type": "scatter"}]
        ]
    )
    
    # Success Rate by Test
    success_by_test = df.groupby('test_name')['success'].mean() * 100
    fig.add_trace(
        go.Bar(
            x=success_by_test.index,
            y=success_by_test.values,
            name='Success Rate (%)',
            marker_color='green'
        ),
        row=1, col=1
    )
    
    # Response Time Distribution
    fig.add_trace(
        go.Box(
            x=df['test_name'],
            y=df['duration_ms'],
            name='Response Time (ms)'
        ),
        row=1, col=2
    )
    
    # Resource Usage
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['memory_mb'],
            name='Memory (MB)',
            mode='lines+markers'
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['cpu_percent'],
            name='CPU (%)',
            mode='lines+markers',
            yaxis='y3'
        ),
        row=2, col=1
    )
    
    # Success Rate Over Time
    df['datetime'] = pd.to_datetime(df['timestamp'])
    success_over_time = df.set_index('datetime')['success'].rolling('1H').mean() * 100
    fig.add_trace(
        go.Scatter(
            x=success_over_time.index,
            y=success_over_time.values,
            name='Success Rate Trend',
            mode='lines'
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        title_text="Cloudflare Bypass Benchmark Results",
        height=1000,
        showlegend=True,
        template="plotly_white"
    )
    
    # Update axes labels
    fig.update_xaxes(title_text="Test Name", row=1, col=1)
    fig.update_xaxes(title_text="Test Name", row=1, col=2)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=2)
    
    fig.update_yaxes(title_text="Success Rate (%)", row=1, col=1)
    fig.update_yaxes(title_text="Duration (ms)", row=1, col=2)
    fig.update_yaxes(title_text="Memory (MB)", row=2, col=1)
    fig.update_yaxes(title_text="Success Rate (%)", row=2, col=2)
    
    # Save or show
    if output_file:
        fig.write_html(output_file)
    else:
        fig.show()

def generate_report(results_file: str, output_file: str = None) -> str:
    """Generate a markdown report from benchmark results."""
    with open(results_file) as f:
        results = json.load(f)
    
    df = pd.DataFrame(results)
    
    report = []
    report.append("# Cloudflare Bypass Benchmark Report")
    report.append(f"\nGenerated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Overall Statistics
    report.append("\n## Overall Statistics")
    report.append(f"- Total Tests: {len(df)}")
    report.append(f"- Overall Success Rate: {df['success'].mean()*100:.2f}%")
    report.append(f"- Average Duration: {df['duration_ms'].mean():.2f}ms")
    report.append(f"- Average Memory Usage: {df['memory_mb'].mean():.2f}MB")
    report.append(f"- Average CPU Usage: {df['cpu_percent'].mean():.2f}%")
    
    # Per-Test Statistics
    report.append("\n## Test Results")
    for test_name in df['test_name'].unique():
        test_df = df[df['test_name'] == test_name]
        report.append(f"\n### {test_name}")
        report.append(f"- Success Rate: {test_df['success'].mean()*100:.2f}%")
        report.append(f"- Average Duration: {test_df['duration_ms'].mean():.2f}ms")
        report.append(f"- Min Duration: {test_df['duration_ms'].min():.2f}ms")
        report.append(f"- Max Duration: {test_df['duration_ms'].max():.2f}ms")
        report.append(f"- Memory Usage: {test_df['memory_mb'].mean():.2f}MB")
        report.append(f"- CPU Usage: {test_df['cpu_percent'].mean():.2f}%")
    
    # Error Analysis
    errors = df[df['error'].notna()]
    if not errors.empty:
        report.append("\n## Errors")
        for _, error in errors.iterrows():
            report.append(f"\n### {error['test_name']}")
            report.append(f"- Timestamp: {error['timestamp']}")
            report.append(f"- Error: {error['error']}")
    
    report_text = "\n".join(report)
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)
    
    return report_text

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        results_file = sys.argv[1]
        create_benchmark_dashboard(results_file, "benchmark_dashboard.html")
        generate_report(results_file, "benchmark_report.md")
    else:
        print("Please provide the path to a benchmark results file") 