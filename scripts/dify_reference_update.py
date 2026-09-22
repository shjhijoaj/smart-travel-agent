"""Run inside the local Dify API container. Inspect first; --apply publishes via services."""
import argparse
import copy
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app_factory import create_app
from extensions.ext_database import db
from models.model import App
from models.account import Account
from models.workflow import Workflow
from services.workflow_service import WorkflowService

parser = argparse.ArgumentParser()
parser.add_argument('--app-id', required=True)
parser.add_argument('--apply', action='store_true')
parser.add_argument('--export', action='store_true')
args = parser.parse_args()
flask_app = create_app()
if isinstance(flask_app, tuple):
    flask_app = flask_app[1]
with flask_app.app_context(), Session(db.engine) as session:
    app = session.get(App, args.app_id)
    if not app:
        raise RuntimeError('Application not found')
    draft = session.scalar(select(Workflow).where(Workflow.app_id == app.id, Workflow.version == 'draft'))
    published = session.get(Workflow, app.workflow_id) if app.workflow_id else None
    graph = copy.deepcopy(draft.graph_dict)
    nodes = {n['id']: n['data'] for n in graph['nodes']}
    planner = nodes['1789999839637']
    retriever = nodes['1789999648884']
    print(json.dumps(dict(mode=app.mode, published_id=app.workflow_id, context=planner['context'],
                          published_context=next((n['data'].get('context') for n in published.graph_dict['nodes']
                                                  if n['id'] == '1789999839637'), None) if published else None,
                          dataset_count=len(retriever.get('dataset_ids', [])), nodes=len(nodes))))
    if args.export:
        from services.app_dsl_service import AppDslService
        exported = AppDslService.export_dsl(app, session=session, include_secret=False, workflow_id=app.workflow_id)
        Path('/tmp/travel-published.yml').write_text(exported, encoding='utf-8')
        print('Published DSL exported without secrets')
    if args.apply:
        backup = dict(app_id=app.id, previous_published_id=app.workflow_id, draft_graph=draft.graph_dict,
                      published_graph=published.graph_dict if published else None)
        Path('/tmp/travel-workflow-before.json').write_text(json.dumps(backup, ensure_ascii=False))
        planner['context'] = dict(enabled=True, variable_selector=['1789999648884', 'result'])
        for prompt in planner.get('prompt_template', []):
            prompt['text'] = prompt['text'].replace('【用户需求】/用户输入 {{#context#}}', '【用户需求】')
            prompt['text'] = prompt['text'].replace('【知识库参考资料】{{#1790000480422.output#}}', '【知识库参考资料】{{#context#}}')
        account = session.get(Account, draft.updated_by or draft.created_by)
        if not account:
            raise RuntimeError('Workflow owner not found')
        service = WorkflowService()
        service.sync_draft_workflow(app_model=app, graph=graph, features=draft.features_dict,
            unique_hash=draft.unique_hash, account=account, environment_variables=draft.environment_variables,
            conversation_variables=draft.conversation_variables, session=session, graph_only=True, commit=False)
        new = service.publish_workflow(session=session, app_model=app, account=account,
                                       marked_name='Travel verified RAG', marked_comment='Bind actual retrieval result to planner context')
        session.flush()
        app.workflow_id = new.id
        session.commit()
        print(json.dumps(dict(published_id=new.id, reference=planner['context'], status='published')))
