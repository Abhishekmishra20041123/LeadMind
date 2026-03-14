import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def load_data():
    print("Loading original datasets...")
    leads_df = pd.read_csv('Leads_Data.csv')
    email_df = pd.read_csv('Email_Logs.csv')
    return leads_df, email_df

def generate_leads(leads_df, target_rows=25000):
    print("Generating Leads_Data.csv...")
    if len(leads_df) > target_rows:
        leads_df = leads_df.sample(n=target_rows, random_state=42).reset_index(drop=True)
    elif len(leads_df) < target_rows:
        # Sample with replacement to reach target rows
        leads_df = leads_df.sample(n=target_rows, replace=True, random_state=42).reset_index(drop=True)
        
    industries = ['Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail', 'Software', 'Consulting']
    
    # Select and rename columns
    df_new = pd.DataFrame()
    
    # Keep original ID to map real emails
    df_new['original_lead_id'] = leads_df['lead_id']
    
    # Generate new clean IDs
    new_ids = ['L' + str(i).zfill(5) for i in range(1, len(df_new) + 1)]
    df_new['lead_id'] = new_ids
    
    df_new['name'] = leads_df['name'] # Keep name for completeness since it is minimum required schema
    df_new['company'] = leads_df['company']
    df_new['title'] = leads_df['title']
    df_new['industry'] = np.random.choice(industries, size=len(df_new))
    df_new['region'] = leads_df['region']
    df_new['visits'] = leads_df['visits'].fillna(0).astype(int)  # agents expect 'visits'
    df_new['pages_per_visit'] = leads_df['pages_per_visit'].fillna(0.0).astype(float)
    df_new['time_on_site'] = leads_df['time_on_site'].fillna(0).astype(int)
    df_new['content_downloads'] = np.random.poisson(lam=0.5, size=len(df_new))
    df_new['lead_source'] = leads_df['lead_source']
    df_new['converted'] = leads_df['converted'].fillna(0).astype(int)
    
    # Add CRM stage
    stages = ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']
    df_new['stage'] = np.random.choice(stages, size=len(df_new), p=[0.3, 0.25, 0.15, 0.1, 0.1, 0.1])
    
    # Add intent_score and status — required by agent pipeline
    df_new['intent_score'] = 0.0
    df_new['status'] = 'New'
    
    # Save the new leads (drop original_lead_id before saving)
    df_save = df_new.drop(columns=['original_lead_id'])
    df_save.to_csv('Leads_Data.csv', index=False)
    print(f"Generated Leads_Data.csv with {len(df_save)} rows.")
    return df_new  # return with original_lead_id for email mapping

def generate_email_history(generated_leads_df):
    print("Generating Email_Logs.csv...")
    
    target_emails = 25000
    # Pick random leads to assign emails to (sampling with replacement to allow ~1-3 emails per lead on average)
    sampled_leads = generated_leads_df.sample(n=target_emails, replace=True, random_state=42).reset_index(drop=True)
    
    df_new = pd.DataFrame()
    df_new['lead_id'] = sampled_leads['lead_id']
    df_new['name'] = sampled_leads['name']
    df_new['company'] = sampled_leads['company']
    
    # Generate realistic email types
    email_types = ['Cold Outreach', 'Follow-up', 'Newsletter', 'Product Update', 'Webinar Invite']
    df_new['email_type'] = np.random.choice(email_types, size=len(df_new), p=[0.4, 0.3, 0.1, 0.1, 0.1])
    
    # Generate realistic copy
    templates = {
        'Cold Outreach': [
            ("Streamlining operations for {company}", "Hi {name}, I noticed {company} is growing rapidly. We help companies like yours save 40% on overhead. Let me know if you are open to a 10-minute demo."),
            ("Your tech stack at {company}", "Hello {name}, Are you currently exploring new ways to automate your workflow at {company}? Our platform integrates seamlessly.")
        ],
        'Follow-up': [
            ("Following up on our conversation", "Hi {name}, Just floating this to the top of your inbox. Let me know if you have any questions from the material I sent over."),
            ("Quick question, {name}?", "Hi {name}, Did you get a chance to review the proposal? Let me know if you'd like to schedule a quick call so we can discuss how this impacts {company}.")
        ],
        'Newsletter': [
            ("The Monthly Tech Digest", "Hi {name}, Here are this month's top strategies for scaling your operations..."),
            ("Industry Insights for {company}", "Hello {name}, We recently published a report on how companies in your space are adapting to the new market changes...")
        ],
        'Product Update': [
            ("New Features Available Now", "Hi {name}, We just launched a massive update to our core platform. Log in to see the new dashboard and analytics tools."),
            ("We've upgraded your account", "Hello {name}, You now have access to our premium AI processing node. We thought {company} might benefit from testing this out.")
        ],
        'Webinar Invite': [
            ("Join our upcoming webinar", "Hi {name}, We're hosting a live session next Thursday on maximizing efficiency. We'd love to see someone from {company} there."),
            ("Exclusive invite for {company}", "Hello {name}, As a valued connection, we're giving you early access to our virtual summit next month. Register today!")
        ]
    }
    
    subjects = []
    texts = []
    for _, row in df_new.iterrows():
        t_type = row['email_type']
        t_list = templates[t_type]
        t = random.choice(t_list)
        c_name = str(row['company']).strip()
        f_name = str(row['name']).strip().split()[0] if str(row['name']).strip() and str(row['name']).strip().lower() != 'nan' else 'there'
        c_name = c_name if c_name and c_name.lower() != 'nan' else 'your company'
        
        subjects.append(t[0].format(name=f_name, company=c_name))
        texts.append(t[1].format(name=f_name, company=c_name))
        
    df_new['subject'] = subjects
    df_new['email_text'] = texts
    
    # Engagement behavior (e.g. 80% open rate)
    df_new['opened'] = np.random.choice([0, 1], size=len(df_new), p=[0.2, 0.8])
    
    # 70% reply rate if opened
    reply_prob = np.random.rand(len(df_new))
    df_new['replied'] = np.where((df_new['opened'] == 1) & (reply_prob < 0.70), 1, 0)
    
    # click_count
    df_new['click_count'] = np.where(df_new['opened'] == 1, np.random.poisson(lam=0.8, size=len(df_new)), 0)
    
    # response_status
    status_map = {1: 'Replied', 0: 'No Reply'}
    df_new['response_status'] = df_new['replied'].map(status_map)
    
    # Drop temp columns
    df_new = df_new.drop(columns=['name', 'company'])
    
    # Add email_id — required by IntentQualifierAgent
    df_new.insert(0, 'email_id', ['E' + str(i).zfill(5) for i in range(1, len(df_new) + 1)])
    
    df_new.to_csv('Email_Logs.csv', index=False)
    print(f"Generated Email_Logs.csv with {len(df_new)} rows.")
    return df_new

def main():
    try:
        leads_df, email_df = load_data()
        generated_leads = generate_leads(leads_df, target_rows=25000)
        generate_email_history(generated_leads)
        print("Dataset generation complete!")
    except Exception as e:
        print(f"Error generating datasets: {e}")

if __name__ == "__main__":
    main()
