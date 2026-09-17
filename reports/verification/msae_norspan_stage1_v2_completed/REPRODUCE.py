import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
m=json.loads((root/'MANIFEST.json').read_text())
for row in m['subjects']:
 p=root/row['path'];s=p.lstat()
 assert s.st_nlink==row['nlink'] and s.st_mode&0o777==row['mode'] and s.st_size==row['bytes']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
assert 'tests/test_prepare_msae_independent_norspan_v1.py' not in m['tests']
out=Path(sys.argv[1]);out.mkdir(mode=0o700)
argv=['/usr/bin/python3.12','-B','-m','pytest','-q','-c','/dev/null','--noconftest','-p','no:cacheprovider','--basetemp='+str(out/'base'),'--junitxml='+str(out/'results.xml')]+m['tests']
(out/'command.json').write_text(json.dumps({'cwd':str(root),'argv':argv,'expected_cases_not_result':1172,'scope':'source_free_regression_only'},indent=2)+'\n')
env=dict(os.environ,TMPDIR='/jumbo/lisp/f004ndc/tmp/lisplab1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
with (out/'run.log').open('xb') as log: result=subprocess.run(argv,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
(out/'exit.txt').write_text(str(result.returncode)+'\n')
raise SystemExit(result.returncode)
