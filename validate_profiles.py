import yaml
import os

print("=" * 60)
print("MULTI-PROFILE CONFIGURATION VALIDATOR")
print("=" * 60)

# Load accounts
with open('credentials/accounts.yaml', 'r') as f:
    data = yaml.safe_load(f)
    accounts = data['accounts']

print(f"\n✅ Found {len(accounts)} account(s) in accounts.yaml\n")

# Chrome User Data directory
chrome_data = os.path.join(os.environ.get('LOCALAPPDATA', r'C:\Users\hr\AppData\Local'), 
                           r'Google\Chrome\User Data')

issues_found = []

for i, acc in enumerate(accounts, 1):
    username = acc.get('username', 'MISSING')
    profile = acc.get('chrome_profile', None)
    
    print(f"{i}. Account: {username}")
    
    if not profile:
        print(f"   ⚠️  WARNING: 'chrome_profile' not specified!")
        print(f"   → Will default to 'Default' profile")
        issues_found.append(f"Account {username} missing chrome_profile")
        profile = 'Default'
    else:
        print(f"   📁 Chrome Profile: '{profile}'")
    
    # Check if profile exists
    profile_path = os.path.join(chrome_data, profile)
    if os.path.exists(profile_path):
        print(f"   ✅ Profile folder found: {profile_path}")
    else:
        print(f"   ❌ ERROR: Profile folder NOT found!")
        print(f"   Expected: {profile_path}")
        issues_found.append(f"Profile '{profile}' not found for {username}")
    
    print()

print("=" * 60)
if issues_found:
    print("⚠️  ISSUES DETECTED:")
    for issue in issues_found:
        print(f"  - {issue}")
    print("\n💡 FIX:")
    print("  1. Check folder names in:", chrome_data)
    print("  2. Update 'chrome_profile' in accounts.yaml to match exact folder names")
else:
    print("✅ All profiles configured correctly!")
    print("   You can run: python main.py")

print("=" * 60)
