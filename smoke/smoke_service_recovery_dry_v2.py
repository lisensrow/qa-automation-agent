"""Fixed wrapper roundtrip/budget + same actual Core guards as v1; no OS writes."""
import base64,gzip,re
from unittest.mock import patch
import service_recovery_dry_v2 as p
import service_recovery_dry_run as old
from smoke import smoke_service_recovery_dry_run as fixture

def main():
 for profile in p.PROFILES:
  payload=p.payload('windows',profile);args=payload['additional_params']['arguments']
  assert len(' '.join(args))+100<8000 and args[-1].startswith('"') and args[-1].endswith('"')
  packed=re.search("FromBase64String\\('([^']+)'\\)",p.wrapper('windows',profile))[1]
  assert gzip.decompress(base64.b64decode(packed)).decode()==p.code('windows',profile)
  assert old.code('windows',p.original(profile)) in p.code('windows',profile)
  assert p.sha('windows',profile)!=old.sha('windows',p.original(profile))
 # Shared fake-native fixture selects v2 but actual endpoint dispatch remains real.
 p.CALLBACK=old.CALLBACK;p.REGISTER_BODY=old.REGISTER_BODY
 with patch.object(fixture,'p',p):fixture.main()
 print('PASS v2 fixed gzip roundtrip/cmd budget/immutable v1/Core guards')

if __name__=='__main__':main()
