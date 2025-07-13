from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Agent(db.Model):
    """Model for registered agents in the system"""
    __tablename__ = 'agents'
    
    id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    persona = db.Column(db.String(50), nullable=False)
    primary_platforms = db.Column(db.Text, nullable=False)  # JSON string
    content_types = db.Column(db.Text, nullable=False)  # JSON string
    posting_frequency = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='active')
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'persona': self.persona,
            'primary_platforms': json.loads(self.primary_platforms),
            'content_types': json.loads(self.content_types),
            'posting_frequency': self.posting_frequency,
            'status': self.status,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AgentMessage(db.Model):
    """Model for inter-agent communications"""
    __tablename__ = 'agent_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_agent_id = db.Column(db.String(100), nullable=False)
    receiver_agent_id = db.Column(db.String(100), nullable=False)
    message_type = db.Column(db.String(50), nullable=False)
    payload = db.Column(db.Text, nullable=False)  # JSON string
    priority = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pending')  # pending, processed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    response = db.Column(db.Text, nullable=True)  # JSON string
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_agent_id': self.sender_agent_id,
            'receiver_agent_id': self.receiver_agent_id,
            'message_type': self.message_type,
            'payload': json.loads(self.payload),
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'response': json.loads(self.response) if self.response else None
        }

class ContentItem(db.Model):
    """Model for content items in the system"""
    __tablename__ = 'content_items'
    
    id = db.Column(db.String(100), primary_key=True)
    creator_agent_id = db.Column(db.String(100), nullable=False)
    persona = db.Column(db.String(50), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content_body = db.Column(db.Text, nullable=False)
    media_urls = db.Column(db.Text, nullable=True)  # JSON string
    hashtags = db.Column(db.Text, nullable=True)  # JSON string
    target_platforms = db.Column(db.Text, nullable=False)  # JSON string
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft, scheduled, published, failed
    performance_metrics = db.Column(db.Text, nullable=True)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'creator_agent_id': self.creator_agent_id,
            'persona': self.persona,
            'content_type': self.content_type,
            'title': self.title,
            'description': self.description,
            'content_body': self.content_body,
            'media_urls': json.loads(self.media_urls) if self.media_urls else [],
            'hashtags': json.loads(self.hashtags) if self.hashtags else [],
            'target_platforms': json.loads(self.target_platforms),
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'status': self.status,
            'performance_metrics': json.loads(self.performance_metrics) if self.performance_metrics else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None
        }

class PlatformAnalytics(db.Model):
    """Model for platform analytics data"""
    __tablename__ = 'platform_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.String(100), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content_id': self.content_id,
            'platform': self.platform,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }

class SystemStatus(db.Model):
    """Model for system status and health monitoring"""
    __tablename__ = 'system_status'
    
    id = db.Column(db.Integer, primary_key=True)
    component = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # healthy, warning, error
    message = db.Column(db.Text, nullable=True)
    metrics = db.Column(db.Text, nullable=True)  # JSON string
    last_check = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'component': self.component,
            'status': self.status,
            'message': self.message,
            'metrics': json.loads(self.metrics) if self.metrics else None,
            'last_check': self.last_check.isoformat() if self.last_check else None
        }

