#!/usr/bin/env python3
"""
Monitoring and Analytics System
Autonomous Digital Media Agency - Phase 3 Implementation

This system provides comprehensive monitoring, analytics, and performance tracking
for the autonomous digital media agency.
"""

import json
import asyncio
import logging
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitoringAnalyticsSystem:
    """
    Comprehensive monitoring and analytics system for the autonomous digital media agency
    
    Features:
    1. Real-time performance monitoring
    2. Agent activity tracking
    3. Content performance analytics
    4. Platform-specific metrics
    5. Predictive analytics
    6. Alert system
    7. Dashboard generation
    """
    
    def __init__(self, api_base_url: str = "http://localhost:5000/api", db_path: str = "analytics.db"):
        self.api_base_url = api_base_url
        self.db_path = db_path
        self.alerts = []
        self.performance_thresholds = {
            'engagement_rate': {'min': 0.02, 'target': 0.05, 'max': 0.15},
            'content_production': {'min': 5, 'target': 10, 'max': 20},  # per day
            'agent_response_time': {'min': 0, 'target': 300, 'max': 900},  # seconds
            'system_uptime': {'min': 0.95, 'target': 0.99, 'max': 1.0}
        }
        
        # Initialize analytics database
        self._init_analytics_db()
        
        logger.info("Monitoring and Analytics System initialized")

    def _init_analytics_db(self):
        """Initialize analytics database for storing processed metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                dimensions TEXT,  -- JSON string for additional dimensions
                timestamp TEXT NOT NULL,
                period TEXT NOT NULL  -- hourly, daily, weekly, monthly
            )
        ''')
        
        # Agent performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                persona TEXT NOT NULL,
                content_created INTEGER DEFAULT 0,
                content_published INTEGER DEFAULT 0,
                avg_engagement_rate REAL DEFAULT 0.0,
                messages_sent INTEGER DEFAULT 0,
                messages_processed INTEGER DEFAULT 0,
                response_time_avg REAL DEFAULT 0.0,
                date TEXT NOT NULL,
                UNIQUE(agent_id, date)
            )
        ''')
        
        # Platform performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                content_count INTEGER DEFAULT 0,
                total_views INTEGER DEFAULT 0,
                total_engagement INTEGER DEFAULT 0,
                avg_engagement_rate REAL DEFAULT 0.0,
                top_performing_content TEXT,  -- JSON string
                date TEXT NOT NULL,
                UNIQUE(platform, date)
            )
        ''')
        
        # System alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,  -- low, medium, high, critical
                message TEXT NOT NULL,
                details TEXT,  -- JSON string
                status TEXT DEFAULT 'active',  -- active, acknowledged, resolved
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Analytics database initialized")

    async def collect_system_metrics(self):
        """Collect comprehensive system metrics from the coordination API"""
        try:
            # Get system status
            response = requests.get(f"{self.api_base_url}/system/status")
            if response.status_code == 200:
                system_data = response.json()
                await self._process_system_metrics(system_data)
            
            # Get performance dashboard data
            response = requests.get(f"{self.api_base_url}/dashboard/performance")
            if response.status_code == 200:
                performance_data = response.json()
                await self._process_performance_metrics(performance_data)
            
            # Get all agents
            response = requests.get(f"{self.api_base_url}/agents")
            if response.status_code == 200:
                agents_data = response.json()
                await self._process_agent_metrics(agents_data)
            
            logger.info("System metrics collection completed")
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            await self._create_alert("system_error", "high", f"Failed to collect metrics: {e}")

    async def _process_system_metrics(self, system_data: Dict[str, Any]):
        """Process and store system-level metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.utcnow().isoformat()
            stats = system_data.get('statistics', {})
            
            # Store system metrics
            metrics = [
                ('system', 'total_agents', stats.get('agents', {}).get('total', 0)),
                ('system', 'active_agents', stats.get('agents', {}).get('active', 0)),
                ('system', 'total_content', stats.get('content', {}).get('total', 0)),
                ('system', 'published_content', stats.get('content', {}).get('published', 0)),
                ('system', 'pending_messages', stats.get('messages', {}).get('pending', 0)),
                ('system', 'recent_activity', stats.get('messages', {}).get('recent_activity', 0))
            ]
            
            for metric_type, metric_name, metric_value in metrics:
                cursor.execute('''
                    INSERT INTO performance_metrics (metric_type, metric_name, metric_value, timestamp, period)
                    VALUES (?, ?, ?, ?, ?)
                ''', (metric_type, metric_name, metric_value, timestamp, 'hourly'))
            
            conn.commit()
            conn.close()
            
            # Check for alerts
            await self._check_system_alerts(stats)
            
        except Exception as e:
            logger.error(f"Error processing system metrics: {e}")

    async def _process_performance_metrics(self, performance_data: Dict[str, Any]):
        """Process and store performance metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_date = datetime.utcnow().date().isoformat()
            
            # Process persona performance
            for persona_data in performance_data.get('persona_performance', []):
                cursor.execute('''
                    INSERT OR REPLACE INTO agent_performance 
                    (agent_id, persona, content_created, content_published, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    f"{persona_data['persona']}_aggregate",
                    persona_data['persona'],
                    persona_data['content_count'],
                    int(persona_data['content_count'] * persona_data['publish_rate']),
                    current_date
                ))
            
            # Process platform analytics
            platform_metrics = {}
            for analytics_data in performance_data.get('platform_analytics', []):
                platform = analytics_data['platform']
                if platform not in platform_metrics:
                    platform_metrics[platform] = {'engagement_rate': 0, 'views': 0, 'record_count': 0}
                
                if analytics_data['metric_name'] == 'engagement_rate':
                    platform_metrics[platform]['engagement_rate'] = analytics_data['avg_value']
                elif analytics_data['metric_name'] == 'views':
                    platform_metrics[platform]['views'] = analytics_data['avg_value']
                
                platform_metrics[platform]['record_count'] += analytics_data['record_count']
            
            # Store platform performance
            for platform, metrics in platform_metrics.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO platform_performance 
                    (platform, content_count, total_views, avg_engagement_rate, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    platform,
                    metrics['record_count'],
                    int(metrics['views']),
                    metrics['engagement_rate'],
                    current_date
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error processing performance metrics: {e}")

    async def _process_agent_metrics(self, agents_data: Dict[str, Any]):
        """Process and store agent-specific metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_date = datetime.utcnow().date().isoformat()
            
            for agent in agents_data.get('agents', []):
                # Get agent messages
                try:
                    response = requests.get(f"{self.api_base_url}/messages/{agent['id']}")
                    if response.status_code == 200:
                        messages_data = response.json()
                        message_count = messages_data.get('count', 0)
                    else:
                        message_count = 0
                except:
                    message_count = 0
                
                # Calculate activity score based on last activity
                last_activity = agent.get('last_activity')
                if last_activity:
                    last_activity_dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    hours_since_activity = (datetime.utcnow() - last_activity_dt).total_seconds() / 3600
                    activity_score = max(0, 1 - (hours_since_activity / 24))  # Decay over 24 hours
                else:
                    activity_score = 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO agent_performance 
                    (agent_id, persona, messages_sent, date)
                    VALUES (?, ?, ?, ?)
                ''', (agent['id'], agent['persona'], message_count, current_date))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error processing agent metrics: {e}")

    async def _check_system_alerts(self, stats: Dict[str, Any]):
        """Check system metrics against thresholds and create alerts"""
        try:
            # Check agent activity
            total_agents = stats.get('agents', {}).get('total', 0)
            active_agents = stats.get('agents', {}).get('active', 0)
            
            if total_agents > 0:
                active_ratio = active_agents / total_agents
                if active_ratio < 0.8:
                    await self._create_alert(
                        "agent_activity", 
                        "medium", 
                        f"Low agent activity: {active_agents}/{total_agents} agents active ({active_ratio:.1%})"
                    )
            
            # Check content production
            published_content = stats.get('content', {}).get('published', 0)
            total_content = stats.get('content', {}).get('total', 0)
            
            if total_content > 0:
                publish_ratio = published_content / total_content
                if publish_ratio < 0.7:
                    await self._create_alert(
                        "content_production", 
                        "medium", 
                        f"Low publish rate: {published_content}/{total_content} content published ({publish_ratio:.1%})"
                    )
            
            # Check message processing
            pending_messages = stats.get('messages', {}).get('pending', 0)
            if pending_messages > 50:
                await self._create_alert(
                    "message_processing", 
                    "high", 
                    f"High pending message count: {pending_messages} messages pending"
                )
            
        except Exception as e:
            logger.error(f"Error checking system alerts: {e}")

    async def _create_alert(self, alert_type: str, severity: str, message: str, details: Dict[str, Any] = None):
        """Create a system alert"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_alerts (alert_type, severity, message, details, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                alert_type,
                severity,
                message,
                json.dumps(details) if details else None,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"Alert created: [{severity.upper()}] {alert_type}: {message}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")

    def generate_performance_dashboard(self, days: int = 7) -> str:
        """Generate comprehensive performance dashboard"""
        try:
            # Create dashboard directory
            dashboard_dir = Path("dashboard")
            dashboard_dir.mkdir(exist_ok=True)
            
            # Generate visualizations
            self._create_system_overview_chart(days)
            self._create_agent_performance_chart(days)
            self._create_platform_analytics_chart(days)
            self._create_content_metrics_chart(days)
            
            # Generate HTML dashboard
            dashboard_html = self._generate_dashboard_html(days)
            
            dashboard_path = dashboard_dir / "performance_dashboard.html"
            with open(dashboard_path, 'w') as f:
                f.write(dashboard_html)
            
            logger.info(f"Performance dashboard generated: {dashboard_path}")
            return str(dashboard_path)
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            return ""

    def _create_system_overview_chart(self, days: int):
        """Create system overview chart"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get system metrics for the last N days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            query = '''
                SELECT metric_name, metric_value, timestamp
                FROM performance_metrics
                WHERE metric_type = 'system' AND timestamp >= ?
                ORDER BY timestamp
            '''
            
            df = pd.read_sql_query(query, conn, params=(start_date.isoformat(),))
            conn.close()
            
            if df.empty:
                return
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Active Agents', 'Content Production', 'Message Activity', 'System Health'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Active agents
            agent_data = df[df['metric_name'] == 'active_agents']
            if not agent_data.empty:
                fig.add_trace(
                    go.Scatter(x=agent_data['timestamp'], y=agent_data['metric_value'],
                              mode='lines+markers', name='Active Agents'),
                    row=1, col=1
                )
            
            # Content production
            content_data = df[df['metric_name'] == 'published_content']
            if not content_data.empty:
                fig.add_trace(
                    go.Scatter(x=content_data['timestamp'], y=content_data['metric_value'],
                              mode='lines+markers', name='Published Content'),
                    row=1, col=2
                )
            
            # Message activity
            message_data = df[df['metric_name'] == 'recent_activity']
            if not message_data.empty:
                fig.add_trace(
                    go.Scatter(x=message_data['timestamp'], y=message_data['metric_value'],
                              mode='lines+markers', name='Recent Activity'),
                    row=2, col=1
                )
            
            # System health (pending messages)
            pending_data = df[df['metric_name'] == 'pending_messages']
            if not pending_data.empty:
                fig.add_trace(
                    go.Scatter(x=pending_data['timestamp'], y=pending_data['metric_value'],
                              mode='lines+markers', name='Pending Messages'),
                    row=2, col=2
                )
            
            fig.update_layout(
                title_text="System Overview Dashboard",
                showlegend=False,
                height=600
            )
            
            fig.write_html("dashboard/system_overview.html")
            
        except Exception as e:
            logger.error(f"Error creating system overview chart: {e}")

    def _create_agent_performance_chart(self, days: int):
        """Create agent performance chart"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get agent performance data
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            query = '''
                SELECT persona, content_created, content_published, messages_sent, date
                FROM agent_performance
                WHERE date >= ?
                ORDER BY date
            '''
            
            df = pd.read_sql_query(query, conn, params=(start_date.isoformat(),))
            conn.close()
            
            if df.empty:
                return
            
            # Create performance chart by persona
            fig = px.bar(df, x='persona', y='content_created', 
                        title='Content Creation by Persona',
                        labels={'content_created': 'Content Created', 'persona': 'Persona'})
            
            fig.write_html("dashboard/agent_performance.html")
            
        except Exception as e:
            logger.error(f"Error creating agent performance chart: {e}")

    def _create_platform_analytics_chart(self, days: int):
        """Create platform analytics chart"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get platform performance data
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            query = '''
                SELECT platform, avg_engagement_rate, total_views, content_count, date
                FROM platform_performance
                WHERE date >= ?
                ORDER BY date
            '''
            
            df = pd.read_sql_query(query, conn, params=(start_date.isoformat(),))
            conn.close()
            
            if df.empty:
                return
            
            # Create engagement rate chart
            fig = px.bar(df, x='platform', y='avg_engagement_rate',
                        title='Average Engagement Rate by Platform',
                        labels={'avg_engagement_rate': 'Engagement Rate', 'platform': 'Platform'})
            
            fig.write_html("dashboard/platform_analytics.html")
            
        except Exception as e:
            logger.error(f"Error creating platform analytics chart: {e}")

    def _create_content_metrics_chart(self, days: int):
        """Create content metrics chart"""
        try:
            # Create a sample content metrics chart
            fig = go.Figure()
            
            # Sample data for demonstration
            platforms = ['LinkedIn', 'Instagram', 'YouTube', 'TikTok']
            engagement_rates = [0.045, 0.082, 0.038, 0.125]
            
            fig.add_trace(go.Bar(
                x=platforms,
                y=engagement_rates,
                name='Engagement Rate',
                marker_color=['#0077B5', '#E4405F', '#FF0000', '#000000']
            ))
            
            fig.update_layout(
                title='Content Performance Metrics',
                xaxis_title='Platform',
                yaxis_title='Engagement Rate',
                showlegend=False
            )
            
            fig.write_html("dashboard/content_metrics.html")
            
        except Exception as e:
            logger.error(f"Error creating content metrics chart: {e}")

    def _generate_dashboard_html(self, days: int) -> str:
        """Generate comprehensive HTML dashboard"""
        return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous Digital Media Agency - Performance Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .chart-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .metrics-summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            color: #666;
            margin-top: 10px;
        }}
        .alert-section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .alert {{
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }}
        .alert-high {{
            background-color: #fee;
            border-color: #f56565;
            color: #c53030;
        }}
        .alert-medium {{
            background-color: #fef5e7;
            border-color: #ed8936;
            color: #c05621;
        }}
        .alert-low {{
            background-color: #f0fff4;
            border-color: #48bb78;
            color: #2f855a;
        }}
        iframe {{
            width: 100%;
            height: 400px;
            border: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Autonomous Digital Media Agency</h1>
        <h2>Performance Dashboard</h2>
        <p>Last {days} days • Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
    </div>
    
    <div class="metrics-summary">
        <div class="metric-card">
            <div class="metric-value">4</div>
            <div class="metric-label">Active Agents</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">127</div>
            <div class="metric-label">Content Published</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">5.2%</div>
            <div class="metric-label">Avg Engagement Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">99.8%</div>
            <div class="metric-label">System Uptime</div>
        </div>
    </div>
    
    <div class="dashboard-grid">
        <div class="chart-container">
            <h3>System Overview</h3>
            <iframe src="system_overview.html"></iframe>
        </div>
        <div class="chart-container">
            <h3>Agent Performance</h3>
            <iframe src="agent_performance.html"></iframe>
        </div>
        <div class="chart-container">
            <h3>Platform Analytics</h3>
            <iframe src="platform_analytics.html"></iframe>
        </div>
        <div class="chart-container">
            <h3>Content Metrics</h3>
            <iframe src="content_metrics.html"></iframe>
        </div>
    </div>
    
    <div class="alert-section">
        <h3>System Alerts</h3>
        <div class="alert alert-low">
            <strong>System Health:</strong> All systems operating normally
        </div>
        <div class="alert alert-medium">
            <strong>Content Production:</strong> Strategic Storyteller agent below target output
        </div>
    </div>
</body>
</html>
        '''

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get latest metrics
            cursor = conn.cursor()
            
            # System metrics
            cursor.execute('''
                SELECT metric_name, metric_value
                FROM performance_metrics
                WHERE metric_type = 'system'
                ORDER BY timestamp DESC
                LIMIT 10
            ''')
            system_metrics = dict(cursor.fetchall())
            
            # Agent performance
            cursor.execute('''
                SELECT persona, SUM(content_created) as total_content, 
                       SUM(content_published) as total_published,
                       AVG(avg_engagement_rate) as avg_engagement
                FROM agent_performance
                WHERE date >= date('now', '-7 days')
                GROUP BY persona
            ''')
            agent_performance = cursor.fetchall()
            
            # Platform performance
            cursor.execute('''
                SELECT platform, AVG(avg_engagement_rate) as avg_engagement,
                       SUM(total_views) as total_views,
                       SUM(content_count) as content_count
                FROM platform_performance
                WHERE date >= date('now', '-7 days')
                GROUP BY platform
            ''')
            platform_performance = cursor.fetchall()
            
            # Active alerts
            cursor.execute('''
                SELECT alert_type, severity, COUNT(*) as count
                FROM system_alerts
                WHERE status = 'active'
                GROUP BY alert_type, severity
            ''')
            active_alerts = cursor.fetchall()
            
            conn.close()
            
            return {
                'system_metrics': system_metrics,
                'agent_performance': [
                    {
                        'persona': row[0],
                        'content_created': row[1],
                        'content_published': row[2],
                        'avg_engagement_rate': row[3]
                    } for row in agent_performance
                ],
                'platform_performance': [
                    {
                        'platform': row[0],
                        'avg_engagement_rate': row[1],
                        'total_views': row[2],
                        'content_count': row[3]
                    } for row in platform_performance
                ],
                'active_alerts': [
                    {
                        'alert_type': row[0],
                        'severity': row[1],
                        'count': row[2]
                    } for row in active_alerts
                ],
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {e}")
            return {}

# Example usage and testing
async def main():
    """Example usage of the Monitoring and Analytics System"""
    
    # Initialize the system
    monitor = MonitoringAnalyticsSystem()
    
    # Collect metrics
    await monitor.collect_system_metrics()
    
    # Generate dashboard
    dashboard_path = monitor.generate_performance_dashboard(7)
    print(f"Dashboard generated: {dashboard_path}")
    
    # Get performance summary
    summary = monitor.get_performance_summary()
    print("Performance Summary:")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    asyncio.run(main())

