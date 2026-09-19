#!/usr/bin/env python3
"""Real app-only lifecycle in disposable storage. No browser launch or profiles.
Requires two extracted compiled apps and exact sibling source archives.
Uses production manager verification, signatures, activity checks and publishing.
"""
import argparse, hashlib, importlib.util, json, shutil, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('delivery',Path(__file__).with_name('manage-terminal-app.py'))
delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery)

def digest(app):
    state=delivery.snapshot(app)
    return hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--older',type=Path,required=True)
    parser.add_argument('--newer',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    if args.receipt.exists():raise ValueError('Receipt already exists')
    roots=[args.older.resolve(),args.newer.resolve()]
    receipt={'scope':'Real compiled app-only lifecycle; no UI, profiles or injected verification', 'results':[], 'fixture_additions':[]}
    work=None
    try:
        apps=[r/'Zen Terminal.app' for r in roots]
        identities=[delivery.identity(a) for a in apps]
        hashes=[digest(a) for a in apps]
        receipt['sources']=[{'path':str(a),'identity':i,'snapshot_sha256':h} for a,i,h in zip(apps,identities,hashes)]
        for root in roots:
            fixture=root/'source/scripts/terminal-tabs/fixtures/firefox156-sessionstore'
            if not fixture.exists():
                shutil.copytree(ROOT/'scripts/terminal-tabs/fixtures/firefox156-sessionstore',fixture)
                receipt['fixture_additions'].append({'path':str(fixture),'reason':'Pristine upstream inputs only, used with this archived checkout\'s own patches; no production source or app edits'})
        work=Path(tempfile.mkdtemp(prefix='compiled-delivery-',dir=ROOT/'.terminal-test'))
        receipt['disposable_directory']=str(work)
        dest=work/'Zen Terminal.app'
        def perform(label,action,index,backup,apply=True,**extra):
            started=time.monotonic();info=identities[index]
            result=delivery.manage(action,dest,work/backup,
                source=None if action=='remove' else apps[index],root=roots[index]/'source',
                expected_version=info['version'],expected_engine=info['engine'],apply=apply,**extra)
            receipt['results'].append({'test':label,'result':'pass','seconds':round(time.monotonic()-started,2),'detail':result})
        def check(label,condition):
            if not condition:raise AssertionError(label)
            receipt['results'].append({'test':label,'result':'pass'})
        perform('dry-run older install','install',0,'unused.app',False)
        check('dry-run creates no installed app or files',not list(work.iterdir()))
        perform('real older install','install',0,'unused.app')
        check('installed older byte/mode snapshot matches source',digest(dest)==hashes[0])
        perform('real newer upgrade retaining older','upgrade',1,'older-retained.app')
        check('upgrade retains exact old and installs exact new',digest(work/'older-retained.app')==hashes[0] and digest(dest)==hashes[1])
        try:
            perform('unacknowledged rollback must fail','rollback',0,'denied.app')
        except ValueError as error:
            check('rollback refuses missing profile-risk acknowledgement without mutation','acknowledgement' in str(error) and digest(dest)==hashes[1] and not (work/'denied.app').exists())
        else:raise AssertionError('Rollback lacked required refusal')
        perform('explicit app-only rollback retaining newer','rollback',0,'newer-retained.app',acknowledge_profile_risk=True)
        check('rollback retains exact new and installs exact old',digest(work/'newer-retained.app')==hashes[1] and digest(dest)==hashes[0])
        perform('app-only removal retains installed app','remove',0,'removed-retained.app')
        check('removal leaves exact retained copy and no installed app',not dest.exists() and digest(work/'removed-retained.app')==hashes[0])
        check('both source apps remain byte/mode identical',[digest(a) for a in apps]==hashes)
        receipt['failure']=None
    except BaseException as error:
        receipt['failure']=f'{type(error).__name__}: {error}'
        raise
    finally:
        if work is not None:
            shutil.rmtree(work)
            receipt['disposable_copies_removed']=not work.exists()
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        args.receipt.write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':main()
