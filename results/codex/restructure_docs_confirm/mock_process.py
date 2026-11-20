"""Inert process table. Never reads real processes or sends real signals."""
import json
import os
from pathlib import Path
import subprocess
import sys

state_path = Path(os.environ['MOCK_STATE'])
state = json.loads(state_path.read_text())
op, *args = sys.argv[1:]
event = {'op': op, 'args': args, 'time': state['time']}
rc = 0
output = []

if op == 'pgrep':
    assert len(args) == 2 and args[0] == '-f', args
    regex = args[1]
    selected = []
    for pid, process in state['processes'].items():
        if not process['alive']:
            continue
        result = subprocess.run(['/usr/bin/grep', '-Eq', '--', regex],
                                input=process['command'] + '\n', text=True)
        assert result.returncode in (0, 1), regex
        if result.returncode == 0:
            selected.append(pid)
    event['selected'] = selected
    output = selected
    rc = 0 if selected else 1
elif op == 'kill':
    probe = args[0] == '-0'
    assert len(args) == (2 if probe else 1), args
    pid = args[-1]
    process = state['processes'].get(pid)
    if process is None:
        rc = 1
        event['error'] = 'ESRCH'
    else:
        mode = process.get('mode', 'terminate')
        if probe and mode == 'exit_before_probe':
            process['alive'] = False
        if not probe and mode == 'exit_before_kill':
            process['alive'] = False
        if not process['alive']:
            rc = 1
            event['error'] = 'ESRCH'
        elif mode == 'permission_denied':
            rc = 1
            event['error'] = 'EPERM'
        elif probe:
            rc = 0
        elif mode in ('fail_alive', 'exit_before_probe'):
            rc = 1
            event['error'] = 'simulated_failed_signal'
        elif mode == 'terminate':
            process['alive'] = False
        elif mode == 'delayed':
            process['exit_time'] = state['time'] + process['delay']
        elif mode != 'stubborn':
            raise AssertionError(mode)
elif op == 'sleep':
    assert len(args) == 1
    state['time'] += int(args[0])
    for process in state['processes'].values():
        if process.get('exit_time', 10**9) <= state['time']:
            process['alive'] = False
    if state['time'] > 90:
        # Bound a broken caller entirely inside the mock; send no signal.
        (state_path.parent / 'logs/local_v4_to_aw.log').write_text('EXPORT FAILED\n')
elif op == 'resume':
    state['resumed'] = args
    rc = state.get('resume_rc', 0)
elif op == 'blocked':
    rc = 125
    event['error'] = 'unexpected_external_operation_blocked'
else:
    raise AssertionError(op)

event['rc'] = rc
state['events'].append(event)
state_path.write_text(json.dumps(state, indent=2) + '\n')
if output:
    print('\n'.join(output))
sys.exit(rc)
