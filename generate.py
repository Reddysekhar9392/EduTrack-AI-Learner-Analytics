import argparse,csv,hashlib,json,random,sqlite3
from pathlib import Path
from datetime import datetime,timedelta,timezone
SEED=20261022
TABLES=['learner','course','cohort','enrollment','content_item','assessment','completion_rule','activity_event','attempt','course_outcome','ground_truth']
SCHEMA='''
CREATE TABLE learner(id TEXT PRIMARY KEY,name TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('active','inactive')),timezone_offset INTEGER NOT NULL);
CREATE TABLE course(id TEXT PRIMARY KEY,title TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('published','archived')));
CREATE TABLE cohort(id TEXT PRIMARY KEY,course_id TEXT NOT NULL REFERENCES course(id),start_date TEXT NOT NULL);
CREATE TABLE enrollment(id TEXT PRIMARY KEY,learner_id TEXT NOT NULL REFERENCES learner(id),course_id TEXT NOT NULL REFERENCES course(id),cohort_id TEXT NOT NULL REFERENCES cohort(id),enrolled_at TEXT NOT NULL,status TEXT NOT NULL,UNIQUE(learner_id,course_id));
CREATE TABLE content_item(id TEXT PRIMARY KEY,course_id TEXT NOT NULL REFERENCES course(id),parent_id TEXT REFERENCES content_item(id),title TEXT NOT NULL,position INTEGER NOT NULL);
CREATE TABLE assessment(id TEXT PRIMARY KEY,course_id TEXT NOT NULL REFERENCES course(id),pass_score INTEGER NOT NULL);
CREATE TABLE completion_rule(id TEXT PRIMARY KEY,course_id TEXT NOT NULL UNIQUE REFERENCES course(id),min_content INTEGER NOT NULL,require_pass INTEGER NOT NULL);
CREATE TABLE activity_event(id TEXT PRIMARY KEY,enrollment_id TEXT REFERENCES enrollment(id),learner_id TEXT NOT NULL REFERENCES learner(id),course_id TEXT NOT NULL REFERENCES course(id),content_id TEXT REFERENCES content_item(id),event_type TEXT NOT NULL,event_time TEXT NOT NULL,received_at TEXT NOT NULL,device TEXT NOT NULL,source_event_key TEXT NOT NULL,issue_type TEXT);
CREATE TABLE attempt(id TEXT PRIMARY KEY,enrollment_id TEXT NOT NULL REFERENCES enrollment(id),assessment_id TEXT NOT NULL REFERENCES assessment(id),score INTEGER NOT NULL,attempted_at TEXT NOT NULL,passed INTEGER NOT NULL);
CREATE TABLE course_outcome(id TEXT PRIMARY KEY,enrollment_id TEXT NOT NULL REFERENCES enrollment(id),status TEXT NOT NULL,decided_at TEXT NOT NULL,reason TEXT NOT NULL);
CREATE TABLE ground_truth(id TEXT PRIMARY KEY,record_id TEXT NOT NULL,issue_type TEXT NOT NULL,expected_decision TEXT NOT NULL);
CREATE INDEX idx_event_enrollment_time ON activity_event(enrollment_id,event_time);
CREATE INDEX idx_event_week ON activity_event(event_time);
CREATE INDEX idx_attempt_enrollment ON attempt(enrollment_id);
'''
def generate(out,learners=200,courses=10,enrollments=1000,events=20000,seed=SEED):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 if enrollments>learners*courses:raise ValueError('Enrollments exceed unique learner-course pairs')
 rng=random.Random(seed);db=out/'edutrack.db'
 if db.exists():db.unlink()
 con=sqlite3.connect(db);con.execute('PRAGMA foreign_keys=ON');con.executescript(SCHEMA)
 base=datetime(2026,9,1,tzinfo=timezone.utc)
 ts=lambda d:d.isoformat(timespec='seconds')
 def batch(table,cols,rows):
  con.executemany(f'INSERT INTO {table} ({",".join(cols)}) VALUES ({",".join("?" for _ in cols)})',rows)
 batch('learner',['id','name','status','timezone_offset'],[(f'LRN-{i:06d}',f'Synthetic Learner {i}', 'inactive' if i%11==0 else 'active',rng.choice([-300,0,330,480])) for i in range(1,learners+1)])
 batch('course',['id','title','status'],[(f'CRS-{i:06d}',f'Course {i}: Learning Path', 'archived' if i%29==0 else 'published') for i in range(1,courses+1)])
 batch('cohort',['id','course_id','start_date'],[(f'COH-{i:06d}',f'CRS-{i:06d}',ts(base+timedelta(days=i%14))) for i in range(1,courses+1)])
 batch('content_item',['id','course_id','parent_id','title','position'],[(f'CNT-{i:06d}-{j:02d}',f'CRS-{i:06d}',None if j==1 else f'CNT-{i:06d}-01',f'Module {j}',j) for i in range(1,courses+1) for j in range(1,5)])
 batch('assessment',['id','course_id','pass_score'],[(f'ASM-2026-{i:06d}',f'CRS-{i:06d}',60) for i in range(1,courses+1)])
 batch('completion_rule',['id','course_id','min_content','require_pass'],[(f'RUL-{i:06d}',f'CRS-{i:06d}',3,1) for i in range(1,courses+1)])
 # Sample unique pairs without generating a huge cross product.
 selected=set()
 while len(selected)<enrollments:selected.add((rng.randrange(1,learners+1),rng.randrange(1,courses+1)))
 pairs=sorted(selected)
 enr=[]
 for li,ci in pairs:
  eid=f'ENR-LRN-{li:06d}-CRS-{ci:06d}'
  enr.append((eid,f'LRN-{li:06d}',f'CRS-{ci:06d}',f'COH-{ci:06d}',ts(base+timedelta(days=ci%14)),'active'))
 batch('enrollment',['id','learner_id','course_id','cohort_id','enrolled_at','status'],enr)
 con.commit()
 # Streaming event creation, bounded memory; every event has a reproducible unique ID.
 event_cols=['id','enrollment_id','learner_id','course_id','content_id','event_type','event_time','received_at','device','source_event_key','issue_type']
 truth=[];buffer=[];event_count={};activity_keys={};completed={};attempts=[]
 for idx in range(events):
  e=enr[rng.randrange(enrollments)];eid,li,ci,coh,start,_=e
  seq=event_count.get(eid,0)+1;event_count[eid]=seq
  event_id=f'EVT-{eid}-{seq:06d}'
  event_type=rng.choices(['view','complete','download'],[5,3,1])[0]
  day=rng.randrange(0,55);event_time=base+timedelta(days=day,hours=rng.randrange(24),minutes=rng.randrange(60))
  device=rng.choice(['web','mobile','offline_sync'])
  issue=None;key=f'K-{idx:09d}'
  if idx%997==0 and idx>0:
   issue='duplicate_event';key=activity_keys.get(eid,key)
  elif idx%1301==0:
   issue='unenrolled_activity'
  elif idx%1601==0:
   issue='timezone_shift'
   event_time=event_time.replace(hour=23,minute=50)
  if issue!='duplicate_event':activity_keys[eid]=key
  if issue=='unenrolled_activity':
   # Preserve anomaly in event stream without invalidating FK relationships.
   eid_ref=None
  else:eid_ref=eid
  received=event_time+timedelta(hours=(48 if device=='offline_sync' else 1))
  row=(event_id,eid_ref,li,ci,f'CNT-{int(ci[-6:]):06d}-{rng.randrange(1,5):02d}',event_type,ts(event_time),ts(received),device,key,issue)
  buffer.append(row)
  if issue:truth.append((f'GT-{len(truth)+1:07d}',event_id,issue,'exclude_from_engagement' if issue in ('duplicate_event','unenrolled_activity') else 'use_event_utc_day'))
  if len(buffer)>=10000:
   batch('activity_event',event_cols,buffer);con.commit();buffer=[]
 if buffer:batch('activity_event',event_cols,buffer)
 con.commit()
 # Attempts are derived with deterministic scores, including repeated attempts.
 for n,e in enumerate(enr):
  eid,li,ci,coh,start,_=e
  for k in range(1,3 if n%7==0 else 2):
   score=(n*37+k*23)%101
   attempts.append((f'ATT-{n+1:07d}-{k}',eid,f'ASM-2026-{int(ci[-6:]):06d}',score,ts(base+timedelta(days=40+k)),int(score>=60)))
 batch('attempt',['id','enrollment_id','assessment_id','score','attempted_at','passed'],attempts)
 con.commit()
 # Completion depends on distinct content completion and a passing assessment.
 rows=con.execute('''SELECT e.id, COUNT(DISTINCT CASE WHEN a.event_type='complete' AND a.issue_type IS NULL THEN a.content_id END) FROM enrollment e LEFT JOIN activity_event a ON a.enrollment_id=e.id GROUP BY e.id''').fetchall()
 passed={r[0] for r in con.execute('SELECT DISTINCT enrollment_id FROM attempt WHERE passed=1')}
 outcomes=[]
 for n,(eid,count) in enumerate(rows):
  done=count>=3 and eid in passed
  outcomes.append((f'OUT-{n+1:07d}',eid,'completed' if done else 'in_progress',ts(base+timedelta(days=60)),f'distinct_content={count};assessment_pass={eid in passed}'))
  if n%503==0:
   truth.append((f'GT-{len(truth)+1:07d}',eid,'premature_completion','reject_completion_before_required_assessment'))
 batch('course_outcome',['id','enrollment_id','status','decided_at','reason'],outcomes)
 batch('ground_truth',['id','record_id','issue_type','expected_decision'],truth)
 con.commit()
 for table in TABLES:
  cur=con.execute(f'SELECT * FROM {table} ORDER BY 1')
  with (out/f'{table}.csv').open('w',newline='',encoding='utf-8') as f:
   w=csv.writer(f);w.writerow([c[0] for c in cur.description]);w.writerows(cur)
 (out/'schema.sql').write_text(SCHEMA)
 counts={t:con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES}
 errors=list(con.execute('PRAGMA foreign_key_check'))
 dup=con.execute('SELECT COUNT(*) FROM (SELECT source_event_key,COUNT(*) n FROM activity_event GROUP BY source_event_key HAVING n>1)').fetchone()[0]
 hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.csv'))}
 manifest={'seed':seed,'counts':counts,'sha256':hashes,'foreign_key_errors':len(errors),'duplicate_event_keys':dup,'synthetic_only':True}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 (out/'validation.json').write_text(json.dumps({'foreign_keys_valid':not errors,'all_primary_keys_unique':True,'row_counts':counts,'duplicate_keys_detected':dup,'completion_rule':'3 distinct completed content items AND at least one passing assessment'},indent=2))
 con.close();return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default='data/starter');p.add_argument('--learners',type=int,default=200);p.add_argument('--courses',type=int,default=10);p.add_argument('--enrollments',type=int,default=1000);p.add_argument('--events',type=int,default=20000);p.add_argument('--seed',type=int,default=SEED);a=p.parse_args();print(json.dumps(generate(a.out,a.learners,a.courses,a.enrollments,a.events,a.seed)['counts'],indent=2))
