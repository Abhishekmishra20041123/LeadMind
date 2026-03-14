import pandas as pd

errors = []

# 1. Check Leads_Data.csv schema
l = pd.read_csv('data/Leads_Data.csv')
e = pd.read_csv('data/Email_Logs.csv')

required_lead_cols = ['lead_id', 'name', 'company', 'title', 'industry', 'region', 'visits',
                      'pages_per_visit', 'time_on_site', 'content_downloads', 'lead_source',
                      'converted', 'stage', 'intent_score', 'status']
required_email_cols = ['email_id', 'lead_id', 'email_type', 'subject', 'email_text',
                       'opened', 'replied', 'click_count', 'response_status']

missing_lead = [c for c in required_lead_cols if c not in l.columns]
missing_email = [c for c in required_email_cols if c not in e.columns]

if missing_lead:
    errors.append(f'LEADS missing cols: {missing_lead}')
if missing_email:
    errors.append(f'EMAILS missing cols: {missing_email}')

# 2. Check relational integrity
email_lead_ids = e['lead_id'].unique()
lead_ids_set = set(l['lead_id'].values)
bad_ids = [x for x in email_lead_ids if x not in lead_ids_set]
if bad_ids:
    errors.append(f'Email lead_ids not found in Leads_Data: {bad_ids[:5]}')

# 3. Check for old schema in batch.py
with open('backend/api/batch.py', 'r') as f:
    batch_content = f.read()
if '"website_visits"' in batch_content and 'rename' not in batch_content:
    errors.append('batch.py still references website_visits without renaming')

# 4. Check smart_upload.py has lead_id in schema
with open('backend/api/smart_upload.py', 'r') as f:
    su_content = f.read()
if '"lead_id"' not in su_content:
    errors.append('smart_upload.py missing lead_id in schema')

# 5. Check generate_content is used (not generate)
if 'llm.generate(' in su_content:
    errors.append('smart_upload.py still uses llm.generate() instead of llm.generate_content()')

# 6. Check intent_qualifier_agent uses visits not website_visits
with open('agents/intent_qualifier_agent.py', 'r') as f:
    iq_content = f.read()
if '"website_visits"' in iq_content and '"visits"' not in iq_content:
    errors.append('intent_qualifier_agent.py still uses website_visits exclusively')

print('=== DATASETS ===')
print(f'Leads: {len(l)} rows, {len(l.columns)} cols')
print(f'Emails: {len(e)} rows, {len(e.columns)} cols')
print(f'Leads cols: {l.columns.tolist()}')
print(f'Email cols: {e.columns.tolist()}')
print()
print('=== RELATIONAL CHECK ===')
matched = sum(1 for eid in e['lead_id'].unique() if eid in lead_ids_set)
total_unique = len(e['lead_id'].unique())
print(f'{matched}/{total_unique} unique email lead_ids match leads ({matched/total_unique*100:.1f}%)')
print()
print('=== CODE CHECKS ===')
print(f'  batch.py lead_id auto-gen: {"conditional (GOOD)" if "if \"lead_id\" not in df.columns" in batch_content else "always overwriting (BAD)"}')
print(f'  batch.py visits field: {"visits (GOOD)" if "visits" in batch_content else "MISSING"}')
print(f'  smart_upload.py method: {"generate_content (GOOD)" if "llm.generate_content" in su_content else "generate (BAD)"}')
print(f'  smart_upload.py lead_id schema: {"present (GOOD)" if "lead_id" in su_content else "missing (BAD)"}')
print(f'  intent_qualifier_agent visits: {"visits (GOOD)" if "visits" in iq_content else "MISSING"}')
print()
if errors:
    print('ERRORS FOUND:')
    for err in errors:
        print(f'  ❌ {err}')
else:
    print('✅ ALL CHECKS PASSED - backend is correctly configured!')
