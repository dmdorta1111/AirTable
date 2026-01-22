import os

step_dir = 'tests/extraction/fixtures/step'
step_files = [f for f in os.listdir(step_dir) if f.endswith('.step') or f.endswith('.stp')]
num_files = len(step_files)

if num_files >= 30:
    print('OK')
else:
    print(f'FAIL: {num_files} files')

print(f'\nTotal STEP files: {num_files}')
print('\nFiles:')
for f in sorted(step_files):
    print(f'  - {f}')
