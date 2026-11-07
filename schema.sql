
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
