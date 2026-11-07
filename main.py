import sqlite3,os
from pathlib import Path
from fastapi import FastAPI,Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from .generate import generate
ROOT=Path(__file__).resolve().parents[1]; DB=Path(os.getenv('EDUTRACK_DB',str(ROOT/'data/starter/edutrack.db')))
if not DB.exists():generate(DB.parent)
app=FastAPI(title='EduTrack AI',version='1.0')
def query(sql,args=()):
 with sqlite3.connect(DB) as c:
  c.row_factory=sqlite3.Row
  return [dict(r) for r in c.execute(sql,args)]
@app.get('/api/summary')
def summary():
 counts={t:query(f'SELECT COUNT(*) n FROM {t}')[0]['n'] for t in ['learner','course','enrollment','activity_event','attempt','ground_truth']}
 completed=query("SELECT COUNT(*) n FROM course_outcome WHERE status='completed'")[0]['n']
 return {'counts':counts,'completed':completed,'completion_rate_pct':round(100*completed/max(counts['enrollment'],1),2)}
@app.get('/api/weekly')
def weekly():
 return query('''SELECT strftime('%Y-W%W',event_time) week,COUNT(DISTINCT enrollment_id) active_enrollments,COUNT(DISTINCT learner_id) active_learners,COUNT(*) raw_events,COUNT(DISTINCT source_event_key) unique_events FROM activity_event WHERE enrollment_id IS NOT NULL AND issue_type IS NULL GROUP BY week ORDER BY week''')
@app.get('/api/cohorts')
def cohorts():
 return query('''SELECT c.id cohort,c.course_id,COUNT(e.id) enrollments,SUM(CASE WHEN o.status='completed' THEN 1 ELSE 0 END) completed,ROUND(100.0*SUM(CASE WHEN o.status='completed' THEN 1 ELSE 0 END)/NULLIF(COUNT(e.id),0),2) completion_pct FROM cohort c LEFT JOIN enrollment e ON e.cohort_id=c.id LEFT JOIN course_outcome o ON o.enrollment_id=e.id GROUP BY c.id ORDER BY c.id''')
@app.get('/api/anomalies')
def anomalies(limit:int=Query(50,ge=1,le=500)):
 return query('SELECT record_id,issue_type,expected_decision FROM ground_truth ORDER BY id LIMIT ?', (limit,))
@app.get('/api/assessments')
def assessments():
 return query('SELECT passed,COUNT(*) attempts FROM attempt GROUP BY passed')
@app.get('/api/validate')
def validate():
 with sqlite3.connect(DB) as c:fk=c.execute('PRAGMA foreign_key_check').fetchall()
 return {'foreign_key_errors':len(fk),'valid':not fk,'completion_rule':'3 distinct completed content items + passing assessment'}
@app.get('/',response_class=HTMLResponse)
def home():return (ROOT/'frontend/index.html').read_text()
