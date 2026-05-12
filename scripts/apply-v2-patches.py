#!/usr/bin/env python3
"""
Apply v2 URL migration patches to Gather's entry.js.
Migrates the app from v1 (app.gather.town) to v2 (app.v2.gather.town).
"""
import os
import sys

ENTRY_JS = sys.argv[1] if len(sys.argv) > 1 else '/tmp/gather-extracted/build/js/entry.js'

with open(ENTRY_JS, 'r', encoding='utf-8', errors='ignore') as f:
    data = f.read()

print(f"BEFORE: v1={data.count('app.gather.town')} v2={data.count('app.v2.gather.town')} size={len(data)}")

# Patch 1: production base URL variable
old1 = 'I="https://app.gather.town"'
new1 = 'I="https://app.v2.gather.town"'
assert old1 in data, "Patch1 missing"
data = data.replace(old1, new1)
print(f"P1 ok. v1={data.count('app.gather.town')} v2={data.count('app.v2.gather.town')}")

# Patch 2: navigation regex
old2 = 'C=/^https:\\/\\/(app|staging|app\\.staging)*[.]*gather\\.town$/'
new2 = 'C=/^https:\\/\\/(app|staging|app\\.staging|app\\.v2)*[.]*gather\\.town$/'
assert old2 in data, "Patch2 missing"
data = data.replace(old2, new2)
print(f"P2 ok. v1={data.count('app.gather.town')} v2={data.count('app.v2.gather.town')}")

# Patch 3: allowed /app URLs (add v2, keep existing)
old3 = 'N2=["https://gather.town/app","https://app.gather.town/app","https://app.staging.gather.town/app"]'
new3 = 'N2=["https://gather.town/app","https://app.gather.town/app","https://app.staging.gather.town/app","https://app.v2.gather.town/app"]'
assert old3 in data, "Patch3 missing"
data = data.replace(old3, new3)
print(f"P3 ok. v1={data.count('app.gather.town')} v2={data.count('app.v2.gather.town')}")

# Patch 4: allowed base domains (add v2, keep existing)
old4 = 'T2=U.BB?["https://gather.town/","https://app.gather.town/","https://app.staging.gather.town/"]:[`${h}/`]' 
new4 = 'T2=U.BB?["https://gather.town/","https://app.gather.town/","https://app.staging.gather.town/","https://app.v2.gather.town/"]:[`${h}/`]' 
assert old4 in data, "Patch4 missing"
data = data.replace(old4, new4)
print(f"P4 ok. v1={data.count('app.gather.town')} v2={data.count('app.v2.gather.town')}")

with open(ENTRY_JS, 'w', encoding='utf-8') as f:
    f.write(data)

with open(ENTRY_JS, 'r', encoding='utf-8', errors='ignore') as f:
    data2 = f.read()

print(f"AFTER WRITE: v1={data2.count('app.gather.town')} v2={data2.count('app.v2.gather.town')} size={len(data2)}")
assert data2.count('app.v2.gather.town') > 0, "Patches did not persist!"
print("SUCCESS")
