from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import json
import uuid
from src.models.agent import db, Agent, AgentMessage, ContentItem, PlatformAnalytics, SystemStatus

agent_bp = Blueprint('agent', __name__)

# Agent Registration and Management
@agent_bp.route('/agents', methods=['POST'])
def register_agent():
    """Register a new agent in the system"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['id', 'name', 'persona', 'primary_platforms', 'content_types', 'posting_frequency']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if agent already exists
        existing_agent = Agent.query.filter_by(id=data['id']).first()
        if existing_agent:
            return jsonify({'error': 'Agent with this ID already exists'}), 409
        
        # Create new agent
        agent = Agent(
            id=data['id'],
            name=data['name'],
            persona=data['persona'],
            primary_platforms=json.dumps(data['primary_platforms']),
            content_types=json.dumps(data['content_types']),
            posting_frequency=data['posting_frequency'],
            status=data.get('status', 'active')
        )
        
        db.session.add(agent)
        db.session.commit()
        
        return jsonify({
            'message': 'Agent registered successfully',
            'agent': agent.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/agents', methods=['GET'])
def get_agents():
    """Get all registered agents"""
    try:
        agents = Agent.query.all()
        return jsonify({
            'agents': [agent.to_dict() for agent in agents],
            'count': len(agents)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """Get specific agent details"""
    try:
        agent = Agent.query.filter_by(id=agent_id).first()
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        
        return jsonify({'agent': agent.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/agents/<agent_id>/status', methods=['PUT'])
def update_agent_status(agent_id):
    """Update agent status and last activity"""
    try:
        agent = Agent.query.filter_by(id=agent_id).first()
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        
        data = request.get_json()
        if 'status' in data:
            agent.status = data['status']
        
        agent.last_activity = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Agent status updated',
            'agent': agent.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Agent Communication
@agent_bp.route('/messages', methods=['POST'])
def send_message():
    """Send message between agents"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['sender_agent_id', 'receiver_agent_id', 'message_type', 'payload']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify sender and receiver exist
        sender = Agent.query.filter_by(id=data['sender_agent_id']).first()
        receiver = Agent.query.filter_by(id=data['receiver_agent_id']).first()
        
        if not sender:
            return jsonify({'error': 'Sender agent not found'}), 404
        if not receiver:
            return jsonify({'error': 'Receiver agent not found'}), 404
        
        # Create message
        message = AgentMessage(
            sender_agent_id=data['sender_agent_id'],
            receiver_agent_id=data['receiver_agent_id'],
            message_type=data['message_type'],
            payload=json.dumps(data['payload']),
            priority=data.get('priority', 1)
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'message': 'Message sent successfully',
            'message_id': message.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/messages/<agent_id>', methods=['GET'])
def get_agent_messages(agent_id):
    """Get messages for a specific agent"""
    try:
        # Verify agent exists
        agent = Agent.query.filter_by(id=agent_id).first()
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        
        # Get query parameters
        status = request.args.get('status', 'pending')
        limit = int(request.args.get('limit', 50))
        
        # Query messages
        messages = AgentMessage.query.filter_by(
            receiver_agent_id=agent_id,
            status=status
        ).order_by(AgentMessage.priority.desc(), AgentMessage.created_at.asc()).limit(limit).all()
        
        return jsonify({
            'messages': [message.to_dict() for message in messages],
            'count': len(messages)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/messages/<int:message_id>/process', methods=['PUT'])
def process_message(message_id):
    """Mark message as processed and optionally add response"""
    try:
        message = AgentMessage.query.get(message_id)
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        data = request.get_json()
        
        message.status = 'processed'
        message.processed_at = datetime.utcnow()
        
        if 'response' in data:
            message.response = json.dumps(data['response'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Message processed successfully',
            'message': message.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Content Management
@agent_bp.route('/content', methods=['POST'])
def create_content():
    """Create new content item"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['creator_agent_id', 'persona', 'content_type', 'title', 'content_body', 'target_platforms', 'scheduled_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify creator agent exists
        creator = Agent.query.filter_by(id=data['creator_agent_id']).first()
        if not creator:
            return jsonify({'error': 'Creator agent not found'}), 404
        
        # Generate content ID if not provided
        content_id = data.get('id', str(uuid.uuid4()))
        
        # Parse scheduled time
        scheduled_time = datetime.fromisoformat(data['scheduled_time'].replace('Z', '+00:00'))
        
        # Create content item
        content = ContentItem(
            id=content_id,
            creator_agent_id=data['creator_agent_id'],
            persona=data['persona'],
            content_type=data['content_type'],
            title=data['title'],
            description=data.get('description', ''),
            content_body=data['content_body'],
            media_urls=json.dumps(data.get('media_urls', [])),
            hashtags=json.dumps(data.get('hashtags', [])),
            target_platforms=json.dumps(data['target_platforms']),
            scheduled_time=scheduled_time,
            status=data.get('status', 'draft')
        )
        
        db.session.add(content)
        db.session.commit()
        
        return jsonify({
            'message': 'Content created successfully',
            'content': content.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/content', methods=['GET'])
def get_content():
    """Get content items with optional filtering"""
    try:
        # Get query parameters
        status = request.args.get('status')
        persona = request.args.get('persona')
        creator_agent_id = request.args.get('creator_agent_id')
        limit = int(request.args.get('limit', 100))
        
        # Build query
        query = ContentItem.query
        
        if status:
            query = query.filter_by(status=status)
        if persona:
            query = query.filter_by(persona=persona)
        if creator_agent_id:
            query = query.filter_by(creator_agent_id=creator_agent_id)
        
        content_items = query.order_by(ContentItem.scheduled_time.asc()).limit(limit).all()
        
        return jsonify({
            'content': [item.to_dict() for item in content_items],
            'count': len(content_items)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/content/<content_id>/status', methods=['PUT'])
def update_content_status(content_id):
    """Update content status"""
    try:
        content = ContentItem.query.filter_by(id=content_id).first()
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        data = request.get_json()
        
        if 'status' in data:
            content.status = data['status']
            
            if data['status'] == 'published':
                content.published_at = datetime.utcnow()
        
        if 'performance_metrics' in data:
            content.performance_metrics = json.dumps(data['performance_metrics'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Content status updated',
            'content': content.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Analytics
@agent_bp.route('/analytics', methods=['POST'])
def record_analytics():
    """Record analytics data for content"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['content_id', 'platform', 'metrics']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify content exists
        content = ContentItem.query.filter_by(id=data['content_id']).first()
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        # Record each metric
        analytics_records = []
        for metric_name, metric_value in data['metrics'].items():
            analytics = PlatformAnalytics(
                content_id=data['content_id'],
                platform=data['platform'],
                metric_name=metric_name,
                metric_value=float(metric_value)
            )
            analytics_records.append(analytics)
            db.session.add(analytics)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Analytics recorded successfully',
            'records_count': len(analytics_records)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/analytics/<content_id>', methods=['GET'])
def get_content_analytics(content_id):
    """Get analytics for specific content"""
    try:
        analytics = PlatformAnalytics.query.filter_by(content_id=content_id).all()
        
        return jsonify({
            'analytics': [record.to_dict() for record in analytics],
            'count': len(analytics)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# System Status and Health
@agent_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """Get overall system status"""
    try:
        # Get agent statistics
        total_agents = Agent.query.count()
        active_agents = Agent.query.filter_by(status='active').count()
        
        # Get content statistics
        total_content = ContentItem.query.count()
        published_content = ContentItem.query.filter_by(status='published').count()
        scheduled_content = ContentItem.query.filter_by(status='scheduled').count()
        
        # Get message statistics
        pending_messages = AgentMessage.query.filter_by(status='pending').count()
        processed_messages = AgentMessage.query.filter_by(status='processed').count()
        
        # Get recent activity
        recent_activity = AgentMessage.query.filter(
            AgentMessage.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return jsonify({
            'system_status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'statistics': {
                'agents': {
                    'total': total_agents,
                    'active': active_agents,
                    'inactive': total_agents - active_agents
                },
                'content': {
                    'total': total_content,
                    'published': published_content,
                    'scheduled': scheduled_content,
                    'draft': total_content - published_content - scheduled_content
                },
                'messages': {
                    'pending': pending_messages,
                    'processed': processed_messages,
                    'recent_activity': recent_activity
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/system/health', methods=['POST'])
def update_system_health():
    """Update system component health status"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['component', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Find or create system status record
        status_record = SystemStatus.query.filter_by(component=data['component']).first()
        
        if status_record:
            status_record.status = data['status']
            status_record.message = data.get('message', '')
            status_record.metrics = json.dumps(data.get('metrics', {}))
            status_record.last_check = datetime.utcnow()
        else:
            status_record = SystemStatus(
                component=data['component'],
                status=data['status'],
                message=data.get('message', ''),
                metrics=json.dumps(data.get('metrics', {}))
            )
            db.session.add(status_record)
        
        db.session.commit()
        
        return jsonify({
            'message': 'System health updated',
            'status': status_record.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Performance Dashboard
@agent_bp.route('/dashboard/performance', methods=['GET'])
def get_performance_dashboard():
    """Get performance dashboard data"""
    try:
        # Get time range from query parameters
        days = int(request.args.get('days', 7))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get content performance by persona
        persona_performance = db.session.execute("""
            SELECT persona, COUNT(*) as content_count, 
                   AVG(CASE WHEN status = 'published' THEN 1.0 ELSE 0.0 END) as publish_rate
            FROM content_items 
            WHERE created_at >= ?
            GROUP BY persona
        """, (start_date,)).fetchall()
        
        # Get platform analytics summary
        platform_analytics = db.session.execute("""
            SELECT platform, metric_name, AVG(metric_value) as avg_value, COUNT(*) as record_count
            FROM platform_analytics 
            WHERE recorded_at >= ?
            GROUP BY platform, metric_name
        """, (start_date,)).fetchall()
        
        # Get agent activity
        agent_activity = db.session.execute("""
            SELECT sender_agent_id, COUNT(*) as message_count
            FROM agent_messages 
            WHERE created_at >= ?
            GROUP BY sender_agent_id
        """, (start_date,)).fetchall()
        
        return jsonify({
            'time_range': f'Last {days} days',
            'persona_performance': [
                {
                    'persona': row[0],
                    'content_count': row[1],
                    'publish_rate': round(row[2], 3)
                } for row in persona_performance
            ],
            'platform_analytics': [
                {
                    'platform': row[0],
                    'metric_name': row[1],
                    'avg_value': round(row[2], 3),
                    'record_count': row[3]
                } for row in platform_analytics
            ],
            'agent_activity': [
                {
                    'agent_id': row[0],
                    'message_count': row[1]
                } for row in agent_activity
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

