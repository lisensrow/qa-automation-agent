import hashlib
import agent_log_presence as old,windows_agent_log_presence_v2 as p
from smoke_agent_log_presence import main
assert p.OLD_ROOT in old.WINDOWS and p.OLD_ROOT not in p.WINDOWS
assert "'USystem\\agentServer'" in p.WINDOWS and "-ine 'bin'" in p.WINDOWS
assert old.sha('windows')!=p.sha('windows')
try:p.payload('astra')
except ValueError:pass
else:raise AssertionError('Windows correction leaked to Astra')
main(p,('windows',),False)
print('PASS Windows source-root correction; v1 immutable; no guard/policy/no-repeat weakening')
