"""Independent enumeration is not plugin identity/renderer/full-case proof."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import gpu_os_baseline as p

def body(name):
    return {'probe_version':1,'platform':name,'query_complete':True,'error':'','rows':[{
        'device_ref':'VideoController1' if name=='windows' else '0000:00:0f.0','device_name':'SVGA II Adapter',
        'vendor_name':None if name=='windows' else 'VMware','vendor_id':'15ad','device_id':'0405',
        'class_id':None if name=='windows' else '0300','device_kind':'video_controller' if name=='windows' else 'pci_display_class'}]}

def main():
    for name in ['windows','astra']:
        obj=body(name);r=p.summarize(obj,name)
        assert r['os_query_complete'] and r['row_count']==1 and not r['plugin_result_compared'] and not r['business_pass']
        assert not r['all_gpu_completeness_verified'] and not r['desktop_or_render_verified']
        for mutate in [lambda x:x.update(probe_version=True),lambda x:x.update(platform='other'),
            lambda x:x['rows'].append(dict(x['rows'][0])),lambda x:x['rows'][0].update(vendor_id='bad'),
            lambda x:x.update(query_complete=False),lambda x:x['rows'][0].update(device_name='')]:
            bad=deepcopy(obj);mutate(bad)
            try:p.summarize(bad,name);raise AssertionError('invalid GPU metadata accepted')
            except ValueError:pass
        incomplete={'probe_version':1,'platform':name,'query_complete':False,'rows':[],'error':'native_gpu_query_failed'}
        assert p.summarize(incomplete,name)['row_count'] is None
        empty=deepcopy(obj);empty['rows']=[];assert p.summarize(empty,name)['row_count']==0 and not p.summarize(empty,name)['all_gpu_completeness_verified']
        assert len(p.sha(name))==64 and p.payload(name)['name']=='executeCommand'
    fixture='Slot:\t0000:00:0f.0\nClass:\tVGA compatible controller [0300]\nVendor:\tVMware [15ad]\nDevice:\tSVGA II Adapter [0405]\n\nSlot:\t0000:00:00.0\nClass:\tHost bridge [0600]\nVendor:\tIntel [8086]\nDevice:\tHost [1237]\n'
    output=[]
    with patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=fixture,stderr='')),patch('builtins.print',side_effect=lambda s:output.append(s)):
        exec(compile(p.ASTRA,'fixed-astra-gpu','exec'),{})
    import json
    assert p.summarize(json.loads(output[0]),'astra')['os_gpu_rows']==body('astra')['rows']
    output=[]
    with patch('subprocess.run',side_effect=FileNotFoundError),patch('builtins.print',side_effect=lambda s:output.append(s)):
        exec(compile(p.ASTRA,'fixed-astra-gpu','exec'),{})
    assert p.summarize(json.loads(output[0]),'astra')['row_count'] is None
    import smoke_drive_os_baseline as fixture_module
    with patch.object(fixture_module,'p',p):
        for name in ['windows','astra']:fixture_module.core_fixture(name,body(name))
    print('GPU OS baseline: PASS (both OS Core/own result/no repeat, unknown/tool failure, PCI scope; fixtures only)')

if __name__=='__main__':main()
