
import csv
import random
from datetime import datetime, timedelta

products = [
    ("Smile Pendant in Yellow Gold, Small", "https://www.tiffany.com/jewelry/necklaces-pendants/tiffany-t-smile-pendant-1364371976.html"),
    ("Smile Pendant in Yellow Gold, Mini", "https://www.tiffany.com/jewelry/necklaces-pendants/tiffany-t-smile-pendant-mini-1364340236.html"),
    ("Open Heart Pendant in Yellow Gold, 11 mm", "https://www.tiffany.com/jewelry/necklaces-pendants/elsa-peretti-open-heart-pendant-11k-yellow-gold-1904359410.html"),
    ("Open Heart Pendant in Yellow Gold, 7 mm", "https://www.tiffany.com/jewelry/necklaces-pendants/elsa-peretti-open-heart-pendant-7k-yellow-gold-1904359402.html"),
    ("Olive Leaf Vine Pendant", "https://www.tiffany.com/jewelry/necklaces-pendants/palomas-olive-leaf-18k-yellow-gold-necklaces-pendants-1904368010.html"),
    ("Olive Leaf Pendant in Yellow Gold with Pearls", "https://www.tiffany.com/jewelry/necklaces-pendants/palomas-olive-leaf-18k-yellow-gold-natural-freshwater-pearl-necklaces-pendants-1904583607.html"),
    ("Love Pendant (Paloma's Graffiti)", "https://www.tiffany.com/jewelry/necklaces-pendants/picasso-graffiti-18k-yellow-gold-necklaces-pendants-1904370941.html"),
    ("Loving Heart Pendant", "https://www.tiffany.com/jewelry/necklaces-pendants/loving-heart-18k-yellow-gold-necklaces-pendants-1904371202.html"),
    ("Diamonds by the Yard® Single Diamond Pendant in Yellow Gold (0.03 ct)", "https://www.tiffany.com/jewelry/necklaces-pendants/ep-diamonds-by-the-yard-18k-yellow-gold-round-brilliant-diamonds-necklaces-pendants-1424550743.html"),
    ("Diamonds by the Yard® Single Diamond Pendant in Yellow Gold (0.05 ct)", "https://www.tiffany.com/jewelry/necklaces-pendants/ep-diamonds-by-the-yard-18k-yellow-gold-round-brilliant-diamonds-necklaces-pendants-1424518852.html"),
    ("Heart Tag Pendant in Rose Gold, Mini", "https://www.tiffany.com/jewelry/necklaces-pendants/return-to-tiffany-18k-rose-gold-necklaces-pendants-1364377759.html"),
    ("Open Heart Pendant in Rose Gold, 7 mm", "https://www.tiffany.com/jewelry/necklaces-pendants/ep-open-heart-18k-rose-gold-necklaces-pendants-1414122376.html"),
    ("Olive Leaf Pendant in Rose Gold", "https://www.tiffany.com/jewelry/necklaces-pendants/18k-rose-gold-round-brilliant-diamonds-necklaces-pendants-1904170050.html"),
    ("Star of David Pendant", "https://www.tiffany.com/jewelry/necklaces-pendants/ep-religious-signs-symbols-18k-yellow-gold-necklaces-pendants-1414152075.html"),
    ("Bean® design Pendant in Yellow Gold, 9 mm", "https://www.tiffany.com/jewelry/necklaces-pendants/ep-bean-18k-yellow-gold-necklaces-pendants-1414152772.html")
]

names = ["James Smith", "Emma Williams", "Liam Brown", "Olivia Jones", "Noah Garcia", "Ava Miller", "Oliver Davis", "Isabella Rodriguez", "William Martinez", "Sophia Hernandez", "Elijah Lopez", "Charlotte Gonzalez", "Lucas Wilson", "Amelia Anderson", "Mason Taylor", "Harper Thomas", "Logan Moore", "Evelyn Jackson", "Alexander Martin", "Abigail Lee", "Ethan Perez", "Emily Thompson", "Jacob White", "Elizabeth Harris", "Michael Sanchez", "Mila Clark", "Daniel Ramirez", "Ella Lewis", "Henry Robinson", "Avery Walker", "Sebastian Young", "Sofia Allen", "Jack King", "Camila Wright", "Samuel Scott", "Aria Torres", "David Nguyen", "Scarlett Hill", "Joseph Adams", "Victoria Flores", "Carter Green", "Madison Nelson", "Owen Baker", "Luna Hall", "Wyatt Rivera", "Grace Campbell", "John Mitchell", "Chloe Carter", "Jack Roberts", "Lily Gomez"]
titles = ["Gift Buyer", "Engagement Shopper", "Jewelry Collector", "Anniversary Buyer", "Fashion Enthusiast", "Wedding Planner", "Luxury Shopper", "Self-Gifting", "Corporate Buyer", "Style Blogger"]
regions = ["North America", "Western Europe", "East Asia", "Asia Pacific", "Latin America", "Europe", "Oceania", "Middle East"]
sources = ["Google Search", "Instagram", "Direct", "Referral", "LinkedIn", "Partnership", "Pinterest", "Forbes Ad", "Facebook", "Word of Mouth"]
stages = ["Initial Contact", "Qualification", "Proposal", "Negotiation", "Closed Won", "Lead"]
statuses = ["Ready", "Hot", "Pending", "Converted", "Cold", "In Progress"]

def generate_leads(count, start_id):
    leads = []
    base_date = datetime(2024, 12, 1)
    for i in range(count):
        prod_name, prod_link = random.choice(products)
        lead_id = f"L_JX_{start_id + i:03d}"
        name = random.choice(names)
        title = random.choice(titles)
        region = random.choice(regions)
        source = random.choice(sources)
        visits = random.randint(1, 15)
        time_on_site = round(random.uniform(1.0, 50.0), 1)
        pages_per_visit = random.randint(1, 12)
        converted = random.choice([True, False])
        stage = random.choice(stages)
        value = random.randint(500, 30000)
        score = random.randint(10, 100)
        status = random.choice(statuses)
        
        engage_date = base_date - timedelta(days=random.randint(0, 60))
        close_date = base_date + timedelta(days=random.randint(0, 30)) if converted else ""
        
        leads.append([
            lead_id, name, title, "Tiffany", region, source, visits, time_on_site, pages_per_visit, converted,
            prod_link, f"OP_JX_{111 + i}", prod_name, stage, value, score, status,
            close_date.strftime("%Y-%m-%d") if close_date else "",
            engage_date.strftime("%Y-%m-%d %H:%M:%S")
        ])
    return leads

if __name__ == "__main__":
    new_leads = generate_leads(90, 11)
    with open("new_leads.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(new_leads)
