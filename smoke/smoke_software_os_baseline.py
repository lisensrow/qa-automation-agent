"""Fixed OS software census scope, no repair/uninstall, Core and no-repeat."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import json
import software_os_baseline as p

def body(name):
    return {'probe_version':1,'platform':name,'query_complete':True,'error':'','rows':[{
        'record_ref':'a'*64 if name=='windows' else 'libc6:amd64','name':'Example' if name=='windows' else 'libc6:amd64',
        'version':'1.2','architecture':'hklm64' if name=='windows' else 'amd64'}]}

def main():
    for name in ['windows','astra']:
        obj=body(name);s=p.summarize(obj,name)
        assert s['os_query_complete'] and s['row_count']==1 and s['full_enumeration_in_own_native_result']
        assert len(s['enumeration_sha256'])==64 and not s['plugin_result_compared'] and not s['all_installed_software_completeness_verified'] and not s['software_tab_verified']
        for mutate in [lambda x:x.update(probe_version=True),lambda x:x.update(platform='other'),lambda x:x['rows'].append(dict(x['rows'][0])),
            lambda x:x.update(query_complete=False),lambda x:x['rows'][0].update(name=''),lambda x:x['rows'][0].update(version='bad\ntext'),
            lambda x:x['rows'][0].update(uninstallString='never execute')]:
            bad=deepcopy(obj);mutate(bad)
            try:p.summarize(bad,name);raise AssertionError('invalid software metadata accepted')
            except ValueError:pass
        blocked={'probe_version':1,'platform':name,'query_complete':False,'rows':[],'error':'native_software_query_failed'}
        assert p.summarize(blocked,name)['row_count'] is None
        empty=deepcopy(obj);empty['rows']=[];assert p.summarize(empty,name)['row_count']==0 and not p.summarize(empty,name)['all_installed_software_completeness_verified']
        many=deepcopy(obj);many['rows']=[dict(obj['rows'][0],record_ref=(f'{i:064x}' if name=='windows' else 'pkg'+str(i)),name=('Example' if name=='windows' else 'pkg'+str(i))) for i in range(13)]
        sample=p.summarize(many,name);assert sample['row_count']==13 and len(sample['sample_rows'])==12 and not sample['sample_is_full_enumeration']
        assert len(p.sha(name))==64 and p.payload(name)['name']=='executeCommand'
    outputs=[]
    fixture='installed\tlibc6:amd64\t1.2\tamd64\nconfig-files\tremoved\t1.1\tall\ninstalled\theld\t2\tall\n'
    def run_fixture(value=None,exc=None):
        outputs.clear()
        with patch('subprocess.run',side_effect=exc,return_value=SimpleNamespace(returncode=0,stdout=value,stderr='')),patch('builtins.print',side_effect=lambda s:outputs.append(s)):
            exec(compile(p.ASTRA,'fixed-astra-software','exec'),{})
        return p.summarize(json.loads(outputs[0]),'astra')
    assert run_fixture(fixture)['row_count']==2
    assert run_fixture(exc=FileNotFoundError)['row_count'] is None
    assert run_fixture('installed\tduplicate\t1\tall\ninstalled\tduplicate\t1\tall\n')['row_count'] is None
    assert run_fixture('installed\tbroken\n')['row_count'] is None
    assert run_fixture('installed\tpkg\t1\tall\n'*2049)['row_count'] is None
    import smoke_drive_os_baseline as fixture_module
    with patch.object(fixture_module,'p',p):
        for name in ['windows','astra']:fixture_module.core_fixture(name,body(name))
    print('software OS baseline: PASS (both-OS Core/policy/own full/no-repeat, native parser unknown/budget, sample scope; fixtures only)')

if __name__=='__main__':main()
